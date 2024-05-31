from .models import Category, Cart, Favorite


def store_menu(request):
    categories = Category.objects.filter(is_active=True)
    context = {
        'categories_menu': categories,
    }
    return context


def cart_menu(request):
    if request.user.is_authenticated:                      #проверка пользователя на аутентификацию
        cart_items= Cart.objects.filter(user=request.user) #получаем объекты из корзины
        context = {
            'cart_items': cart_items,
        }
    else:
        context = {}
    return context


def favorites_count(request):
    if request.user.is_authenticated:
        count = Favorite.objects.filter(user=request.user).count()
    else:
        count = 0
    return {'favorites_count': count}
