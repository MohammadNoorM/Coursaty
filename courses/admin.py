from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import Category, Course, Section, Lesson, Enrollment, Rating, Comment


@admin.register(Category)
class CategoryAdmin(TranslationAdmin):
    list_display = ('name', 'slug')


class SectionInline(admin.StackedInline):
    model = Section
    extra = 1


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1


@admin.register(Course)
class CourseAdmin(TranslationAdmin):
    list_display = ('title', 'category', 'price', 'is_published', 'created_at')
    list_filter = ('is_published', 'category')
    search_fields = ('title',)
    inlines = [SectionInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Section)
class SectionAdmin(TranslationAdmin):
    list_display = ('title', 'course', 'order')
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(TranslationAdmin):
    list_display = ('title', 'section', 'order')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'enrolled_at')
    list_filter = ('course',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'score', 'created_at')
    list_filter = ('score', 'course')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'created_at')