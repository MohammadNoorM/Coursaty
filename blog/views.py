from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Post
from .forms import PostForm
from django.utils.translation import gettext_lazy as _

def post_list(request):
    if request.user.is_authenticated and request.GET.get('mine'):
        post_list_qs = Post.objects.filter(author=request.user)
    else:
        post_list_qs = Post.objects.all()
        
    paginator = Paginator(post_list_qs, 9) # Show 9 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(number=page_obj.number, on_each_side=1, on_ends=1)
    
    context = {
        'posts': page_obj, 
        'page_obj': page_obj, 
        'page_range': page_range,
        'showing_mine': request.GET.get('mine') == 'true'
    }
    return render(request, 'blog/post_list.html', context)

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    return render(request, 'blog/post_detail.html', {'post': post})

@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, _('Post created successfully!'))
            return redirect('blog:post_detail', slug=post.slug)
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form})

@login_required
def post_edit(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, _('Post updated successfully!'))
            return redirect('blog:post_detail', slug=post.slug)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_form.html', {'form': form, 'post': post})

@login_required
def post_delete(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    if request.method == 'POST':
        post.delete()
        messages.success(request, _('Post deleted.'))
        return redirect('blog:post_list')
    return render(request, 'blog/post_confirm_delete.html', {'post': post})
