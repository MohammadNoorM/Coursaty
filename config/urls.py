from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
import django.conf.urls.i18n

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('', include('courses.urls')),
    path('accounts/', include('accounts.urls')),
    path('payments/', include('payments.urls')),
    path('blog/', include('blog.urls')),
]