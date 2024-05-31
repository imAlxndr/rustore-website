import django
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from store.models import Address, Cart, Category, Order, Product, Review, Favorite
from django.shortcuts import redirect, render, get_object_or_404
from .forms import RegistrationForm, AddressForm, ReviewForm
from django.contrib import messages
from django.views import View
import decimal
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


def home(request):  # получаем категории и товары на главной странице
    categories = Category.objects.filter(is_active=True, is_featured=True)[:3]
    products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    context = {
        'categories': categories,
        'products': products,
    }
    return render(request, 'store/index.html', context)


def about_company(request):
    return render(request, 'store/about_company.html')


def search(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(title__icontains=query)
    return render(request, 'store/search_results.html', {'products': products, 'query': query})


def detail(request, slug):  # получаем инфу о товаре и похожий товар
    product = get_object_or_404(Product, slug=slug)
    related_products = Product.objects.exclude(id=product.id).filter(is_active=True, category=product.category)
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    for review in reviews:
        review.stars = range(review.rating)  # Создаем список звезд для каждого отзыва
        review.empty_stars = range(5 - review.rating)  # Создаем список пустых звезд

    if request.method == 'POST':
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.product = product
            review.user = request.user  # Убедитесь, что пользователь авторизован
            review.save()
            return redirect('store:product-detail', slug=slug)
    else:
        review_form = ReviewForm()

    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'review_form': review_form,
    }
    return render(request, 'store/detail.html', context)


def all_categories(request):  # получаем все категории
    categories = Category.objects.filter(is_active=True)
    return render(request, 'store/categories.html', {'categories': categories})


def category_products(request, slug):  # получаем категории
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(is_active=True, category=category)
    categories = Category.objects.filter(is_active=True)

    # Получение параметров фильтрации из запроса
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    # Применение фильтров по цене
    if price_min:
        products = products.filter(price__gte=price_min)
    if price_max:
        products = products.filter(price__lte=price_max)

    # Фильтры "Показать только"
    returnable = request.GET.get('returnable')
    in_stock = request.GET.get('in_stock')
    sold = request.GET.get('sold')
    discount = request.GET.get('discount')

    if 'returnable' in request.GET:
        products = products.filter(returnable=True)
    if 'in_stock' in request.GET:
        products = products.filter(in_stock=True)
    if 'sold' in request.GET:
        products = products.filter(sold=True)
    if 'discount' in request.GET:
        products = products.filter(discount=True)

    # Фильтры "Формат покупки"
    purchase_format = request.GET.get('buy_format')
    # Применение фильтра по формату покупки
    if purchase_format == 'best_offer':
        # Фильтр для товаров с лучшим предложением
        products = products.filter(best_offer=True)
    elif purchase_format == 'buy_now':
        # Фильтр для товаров, которые можно купить сразу
        products = products.filter(buy_now=True)
    # Если выбрано "Все объявления" или параметр не задан, фильтр не применяется


    # Применение сортировки (популярное, по возрастанию и убыванию)
    sorting = request.GET.get('sorting')  # Получаем параметр сортировки
    if sorting == 'low-high':
        products = products.order_by('price')
    elif sorting == 'high-low':
        products = products.order_by('-price')
    elif sorting == 'popularity':
        products = products.order_by('-best_offer')

    # Настройка пагинации
    paginator = Paginator(products, 12)  # Показывать по 12 товаров на странице
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    context = {
        'category': category,
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/category_products.html', context)


# Authentication Starts Here

class RegistrationView(View):  # получаем форму регистрации
    def get(self, request):
        form = RegistrationForm()
        return render(request, 'account/register.html', {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            messages.success(request, "Регистрация прошла успешно!")
            form.save()
        return render(request, 'account/register.html', {'form': form})


@login_required  # Декоратор для представлений, который проверяет, что пользователь вошел в систему, перенаправляя
# на страницу входа, если это необходимо.
def profile(request):  # профиль пользователя, вывод адреса и заказов
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user)
    return render(request, 'account/profile.html', {'addresses': addresses, 'orders': orders})


@method_decorator(login_required, name='dispatch')
class AddressView(View):  # добавление адреса
    def get(self, request):
        form = AddressForm()
        return render(request, 'account/add_address.html', {'form': form})

    def post(self, request):
        form = AddressForm(request.POST)
        if form.is_valid():
            user = request.user
            locality = form.cleaned_data['locality']
            city = form.cleaned_data['city']
            state = form.cleaned_data['state']
            reg = Address(user=user, locality=locality, city=city, state=state)
            reg.save()
            messages.success(request, "Адрес упешно добавлен.")
        return redirect('store:profile')


@login_required  # Декоратор для представлений, который проверяет, что пользователь вошел в систему, перенаправляя
# на страницу входа, если это необходимо.
def remove_address(request, id):  # удаление адреса
    a = get_object_or_404(Address, user=request.user, id=id)
    a.delete()
    messages.success(request, "Адрес удален.")
    return redirect('store:profile')


@login_required  # Декоратор для представлений, который проверяет, что пользователь вошел в систему, перенаправляя
# на страницу входа, если это необходимо.
def add_to_cart(request):  # добавление товара в корзину
    user = request.user
    product_id = request.GET.get('prod_id')
    product = get_object_or_404(Product, id=product_id)

    # Проверка, есть ли товар в корзине или нет
    item_already_in_cart = Cart.objects.filter(product=product_id, user=user)
    if item_already_in_cart:
        cp = get_object_or_404(Cart, product=product_id, user=user)
        cp.quantity += 1
        cp.save()
    else:
        Cart(user=user, product=product).save()

    return redirect('store:cart')


@login_required  # Декоратор для представлений, который проверяет, что пользователь вошел в систему, перенаправляя
# на страницу входа, если это необходимо.
def cart(request):  # корзина
    user = request.user
    cart_products = Cart.objects.filter(user=user)

    # Показывает итог на странице корзины
    amount = decimal.Decimal(0)
    shipping_amount = decimal.Decimal(250)
    # список для расчета общей суммы на основе количества и стоимости
    cp = [p for p in Cart.objects.all() if p.user == user]
    if cp:
        for p in cp:
            temp_amount = (p.quantity * p.product.price)
            amount += temp_amount

    # Customer Addresses
    addresses = Address.objects.filter(user=user)

    context = {
        'cart_products': cart_products,
        'amount': amount,
        'shipping_amount': shipping_amount,
        'total_amount': amount + shipping_amount,
        'addresses': addresses,
    }
    return render(request, 'store/cart.html', context)


@login_required  # Декоратор для представлений, который проверяет, что пользователь вошел в систему, перенаправляя
# на страницу входа, если это необходимо.
def remove_cart(request, cart_id):  # удаление товара из корзины
    if request.method == 'GET':
        c = get_object_or_404(Cart, id=cart_id)
        c.delete()
        messages.success(request, "Товар удален из корзины.")
    return redirect('store:cart')


@login_required
def add_to_favorites(request):
    user = request.user
    product_id = request.GET.get('prod_id')
    product = get_object_or_404(Product, id=product_id)

    # Создаем избранное, если еще нет
    favorite, created = Favorite.objects.get_or_create(user=user, product=product)

    if created:
        messages.success(request, "Товар добавлен в избранное.")
    else:
        messages.info(request, "Товар уже в избранном.")

    return redirect('store:favorites')  # Перенаправляем на страницу с избранными товарами



@login_required
def favorites(request):
    user = request.user
    favorites = Favorite.objects.filter(user=user)
    context = {
        'favorites': favorites,
    }
    return render(request, 'store/favorites.html', context)


@login_required
def remove_from_favorites(request, favorite_id):
    favorite = get_object_or_404(Favorite, id=favorite_id, user=request.user)
    favorite.delete()
    return redirect('store:favorites')


@login_required  # Декоратор для представлений, который проверяет, что пользователь вошел в систему, перенаправляя
# на страницу входа, если это необходимо.
def plus_cart(request, cart_id):  # прибавление 1 товар в количество в корзине
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        cp.quantity += 1
        cp.save()
    return redirect('store:cart')


@login_required  # Декоратор для представлений, который проверяет, что пользователь вошел в систему, перенаправляя
# на страницу входа, если это необходимо.
def minus_cart(request, cart_id):  # удаляет 1 товар в количество в корзине
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        # удаляет товар если количество = 1
        if cp.quantity == 1:
            cp.delete()
        else:
            cp.quantity -= 1
            cp.save()
    return redirect('store:cart')


@login_required  # Декоратор для представлений, который проверяет, что пользователь вошел в систему, перенаправляя
# на страницу входа, если это необходимо.
def checkout(request):  # оформление заказа
    user = request.user
    order = Order.objects.filter(user=user).last()
    cart_products = Cart.objects.filter(user=user)

    # Показывает итог на странице заказа
    amount = decimal.Decimal(0)
    shipping_amount = decimal.Decimal(250)
    # список для расчета общей суммы на основе количества и стоимости
    cp = [p for p in Cart.objects.all() if p.user == user]
    if cp:
        for p in cp:
            temp_amount = (p.quantity * p.product.price)
            amount += temp_amount

    # Customer Addresses
    addresses = Address.objects.filter(user=user)
    store_address = {
        'locality': 'ул. Карла Маркса, д. 125',
        'city': 'Красноярск',
        'state': 'Центральный район'
    }

    context = {
        'order': order,
        'cart_products': cart_products,
        'amount': amount,
        'shipping_amount': shipping_amount,
        'total_amount': amount + shipping_amount,
        'addresses': addresses,
        'store_address': store_address,
    }

    if request.method == 'POST':
        # Здесь должен быть код для обработки платежа
        # Например, вызов API платежной системы
        payment_result = process_payment(request)

        if payment_result['success']:
            address_id = request.POST.get('address')
            address = get_object_or_404(Address, id=address_id, user=user)

            for item in cart_products:
                Order(user=user, address=address, product=item.product, quantity=item.quantity).save()
                item.delete()

            # Перенаправление на страницу подтверждения заказа
            return redirect('store:order-confirmation')
        else:
            # Обработка случая, когда платеж не прошел
            pass

        delivery_method = request.POST.get('delivery_method')
        payment_method = request.POST.get('payment_method')

        if payment_method == 'card':
            # Здесь должен быть код для обработки данных карты
            card_number = request.POST.get('card_number')
            card_expiry = request.POST.get('card_expiry')
            card_cvc = request.POST.get('card_cvc')
            # Вызов API платежной системы для обработки платежа

        if delivery_method == 'pickup':
            # Установка адреса магазина для самовывоза
            address = store_address
        elif delivery_method == 'delivery':
            # Использование существующего адреса пользователя
            address_id = request.POST.get('address')
            address = get_object_or_404(Address, id=address_id, user=user)

    return render(request, 'store/checkout.html', context)


def process_payment(request):
    # Здесь должен быть код для обработки платежа
    # Это просто пример и не реальный код
    return {'success': True}


@login_required
def order_confirmation(request):
    user = request.user
    # Получаем последний заказ пользователя
    order = Order.objects.filter(user=user).last()

    if not order:
        # Если заказ не найден, перенаправляем на главную страницу или страницу с корзиной
        return redirect('store:home')

    context = {
        'order': order,
    }
    return render(request, 'store/order_confirmation.html', context)


@login_required  # Декоратор для представлений, который проверяет, что пользователь вошел в систему, перенаправляя
# на страницу входа, если это необходимо.
def orders(request):  # заказ
    all_orders = Order.objects.filter(user=request.user).order_by('-ordered_date')
    return render(request, 'store/orders.html', {'orders': all_orders})