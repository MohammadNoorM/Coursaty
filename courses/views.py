from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Course, Lesson, Comment, Enrollment, Category

def home_view(request):
    featured_courses = Course.objects.filter(is_published=True).order_by('-created_at')[:6]
    categories = Category.objects.all()
    return render(request, 'courses/home.html',
                  {'featured_courses': featured_courses,
                   'categories': categories
                   })

def course_list_view(request):
    courses = Course.objects.filter(is_published=True).order_by('-created_at')
    categories = Category.objects.all()

    category_slug = request.GET.get('category')
    if category_slug:
        courses = courses.filter(category__slug=category_slug)
    
    search_query = request.GET.get('q')
    if search_query:
        courses = courses.filter(title__icontains=search_query)
    
    return render(request, 'courses/course_list.html',
                  {'courses': courses,
                   'categories': categories,
                   'selected_category': category_slug,
                   'search_query': search_query
                   })

def course_detail_view(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    is_enrolled = False
    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    
    # what_you_learn and requirements stored as line-separated text
    what_you_learn = [
        line.strip() for line in course.what_you_learn.splitlines() 
        if line.strip()
        ] if course.what_you_learn else []
    
    requirements = [
        line.strip() for line in course.requirements.splitlines()
        if line.strip()
    ] if course.requirements else []

    template_name = 'courses/course_detail_enrolled.html' if is_enrolled else 'courses/course_detail.html'
    return render(request, template_name,
                  {'course': course,
                   'is_enrolled': is_enrolled,
                   'what_you_learn': what_you_learn,
                   'requirements': requirements
                   })

@login_required
def dashboard_view(request):
    enrollments = Enrollment.objects.filter(user=request.user).select_related('course')
    return render(request, 'courses/dashboard.html',
                  {'enrollments': enrollments
                   })

@login_required
def lesson_view(request, course_slug, lesson_slug):
    course = get_object_or_404(Course, slug=course_slug, is_published=True)

    # Access control — must be enrolled
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.error(request, "You must purchase this course to access lessons.")
        return redirect('courses:course_detail', slug=course_slug)
    
    lesson = get_object_or_404(Lesson, slug=lesson_slug, section__course=course)
    comments = Comment.objects.filter(lesson=lesson, parent=None).prefetch_related('replies__user').select_related('user')

    return render(request, 'courses/lesson.html',
                  {'course': course,
                   'lesson': lesson,
                     'comments': comments
                     })

@login_required
def add_comment(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.section.course

    # Must be enrolled to comment
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.error(request, "You must be enrolled to comment.")
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