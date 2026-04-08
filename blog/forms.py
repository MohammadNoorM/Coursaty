from django import forms
from .models import Post
from django.utils.translation import gettext_lazy as _

class PostForm(forms.ModelForm):
    title = forms.CharField(label=_('Title'), max_length=200)
    cover_image = forms.ImageField(label=_('Cover Image'), required=False)
    excerpt = forms.CharField(label=_('Excerpt'), max_length=300)
    body = forms.CharField(label=_('Body'), widget=forms.Textarea)

    class Meta:
        model = Post
        fields = ['title', 'cover_image', 'excerpt', 'body']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'w-full bg-surface-container-low border-none rounded-lg p-4 text-on-surface focus:ring-2 focus:ring-primary/20'