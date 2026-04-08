from django.db import models
from django.conf import settings
from autoslug import AutoSlugField
from courses.models import custom_slugify
from django.utils.translation import gettext_lazy as _

class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='posts')
    title = models.CharField(max_length=200)
    slug = AutoSlugField(populate_from='title', unique=True, slugify=custom_slugify)
    cover_image = models.ImageField(upload_to='courses/blog/', blank=True, null=True)
    excerpt = models.CharField(max_length=300)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('Post')
        verbose_name_plural = _('Posts')
        ordering = ['-created_at']
