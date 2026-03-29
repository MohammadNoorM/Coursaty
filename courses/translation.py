from modeltranslation.translator import register, TranslationOptions
from .models import Category, Course, Section, Lesson


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Course)
class CourseTranslationOptions(TranslationOptions):
    fields = ('title', 'short_description', 'description', 'what_you_learn', 'requirements')


@register(Section)
class SectionTranslationOptions(TranslationOptions):
    fields = ('title',)


@register(Lesson)
class LessonTranslationOptions(TranslationOptions):
    fields = ('title',)