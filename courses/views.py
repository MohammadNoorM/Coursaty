from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg
from django.http import JsonResponse
from .models import Course, Lesson, Comment, Enrollment, Category, Rating, Wishlist
from django.utils.translation import gettext_lazy as _

from django.contrib.auth import get_user_model

def home_view(request):
    featured_courses = Course.objects.filter(is_published=True).order_by('-created_at')[:6]
    categories = Category.objects.all()
    
    course_count = Course.objects.filter(is_published=True).count()
    lesson_count = Lesson.objects.filter(section__course__is_published=True).count()
    learner_count = get_user_model().objects.filter(is_active=True).count()
    
    avg_rating = Rating.objects.aggregate(avg=Avg('score'))['avg'] or 0.0
    rating_count = Rating.objects.count()
    success_rate = int((avg_rating / 5) * 100) if avg_rating else 100
    
    return render(request, 'courses/home.html',
                  {'featured_courses': featured_courses,
                   'categories': categories,
                   'course_count': course_count,
                   'lesson_count': lesson_count,
                   'learner_count': learner_count,
                   'success_rate': success_rate,
                   'avg_rating': avg_rating,
                   'rating_count': rating_count,
                   })

def course_list_view(request):
    courses = Course.objects.filter(is_published=True).annotate(
        avg_rating=Avg('ratings__score')
    ).order_by('-created_at')
    categories = Category.objects.all()

    category_slug = request.GET.get('category')
    if category_slug:
        courses = courses.filter(category__slug=category_slug)
    
    search_query = request.GET.get('q')
    if search_query:
        courses = courses.filter(title__icontains=search_query)

    min_rating = request.GET.get('rating')
    if min_rating:
        try:
            min_val = float(min_rating)
            if min_val > 0:
                courses = courses.filter(avg_rating__gte=min_val)
        except ValueError:
            pass

    sort_by = request.GET.get('sort')
    if sort_by == 'newest':
        courses = courses.order_by('-created_at')
    elif sort_by == 'rating':
        courses = courses.order_by('-avg_rating')
    elif sort_by == 'price_low':
        courses = courses.order_by('price')

    paginator = Paginator(courses, 12) # 12 courses per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Generate pagination range with ellipses for first/last pages
    page_range = paginator.get_elided_page_range(number=page_obj.number, on_each_side=1, on_ends=1)

    return render(request, 'courses/course_list.html',
                  {'courses': page_obj,
                   'categories': categories,
                   'selected_category': category_slug,
                   'search_query': search_query,
                   'min_rating': min_rating,
                   'sort_by': sort_by,
                   'page_obj': page_obj,
                   'page_range': page_range
                   })

def course_detail_view(request, slug):
    course = get_object_or_404(
        Course.objects.annotate(
            avg_rating=Avg('ratings__score')
        ),
        slug=slug, 
        is_published=True
    )
    is_enrolled = False
    is_saved = False
    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
        is_saved = Wishlist.objects.filter(user=request.user, course=course).exists()
        
    student_count = course.enrollments.count()
    rating_count = course.ratings.count()
    
    # what_you_learn and requirements stored as line-separated text
    what_you_learn = [
        line.strip().lstrip('- ') for line in course.what_you_learn.splitlines() 
        if line.strip()
    ] if course.what_you_learn else []
    
    requirements = [
        line.strip().lstrip('- ') for line in course.requirements.splitlines()
        if line.strip()
    ] if course.requirements else []

    template_name = 'courses/course_detail_enrolled.html' if is_enrolled else 'courses/course_detail.html'
    return render(request, template_name,
                  {'course': course,
                   'is_enrolled': is_enrolled,
                   'is_saved': is_saved,
                   'what_you_learn': what_you_learn,
                   'requirements': requirements,
                   'student_count': student_count,
                   'rating_count': rating_count
                   })

@login_required
def dashboard_view(request):
    enrollments = Enrollment.objects.filter(user=request.user).select_related('course')
    saved_courses = Wishlist.objects.filter(user=request.user).select_related('course')
    active_tab = request.GET.get('tab', 'enrolled')
    return render(request, 'courses/dashboard.html', {
        'enrollments': enrollments,
        'saved_courses': saved_courses,
        'active_tab': active_tab,
    })

@login_required
def lesson_view(request, course_slug, lesson_slug):
    course = get_object_or_404(Course, slug=course_slug, is_published=True)

    # Access control — must be enrolled
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.error(request, _("You must purchase this course to access lessons."))
        return redirect('courses:course_detail', slug=course_slug)
    
    lesson = get_object_or_404(Lesson, slug=lesson_slug, section__course=course)
    comments = Comment.objects.filter(lesson=lesson, parent=None).prefetch_related('replies__user').select_related('user')

    all_lessons = list(Lesson.objects.filter(section__course=course).select_related('section').order_by('section__order', 'order'))
    try:
        current_index = all_lessons.index(lesson)
        next_lesson = all_lessons[current_index + 1]
    except (ValueError, IndexError):
        next_lesson = None

    return render(request, 'courses/lesson.html',
                  {'course': course,
                   'lesson': lesson,
                   'comments': comments,
                   'next_lesson': next_lesson
                   })

@login_required
def add_comment(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.section.course

    # Must be enrolled to comment
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.error(request, _("You must be enrolled to comment."))
        return redirect('courses:course_detail', slug=course.slug)
    
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        parent_id = request.POST.get('parent_id')
        if body:
            parent = Comment.objects.get(id=parent_id) if parent_id else None
            Comment.objects.create(
                user=request.user,
                lesson=lesson,
                body=body,
                parent=parent
            )
    return redirect('courses:lesson', course_slug=course.slug, lesson_slug=lesson.slug)

@login_required
def toggle_wishlist(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, course=course)
    if not created:
        wishlist_item.delete()
        saved = False
    else:
        saved = True
    return JsonResponse({'saved': saved})