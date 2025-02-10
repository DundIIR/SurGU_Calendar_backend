from django.contrib import admin
from .models import *


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'password', 'date_joined', 'last_login', 'professor', 'student', 'role')
    list_display_links = ('email',)


class StudentAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'patronymic', 'course')
    list_display_links = ('last_name',)


class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'patronymic', 'post', 'department', 'file')
    list_display_links = ('last_name',)


class GroupAdmin(admin.ModelAdmin):
    list_display = ('number_group', 'speciality')
    list_display_links = ('number_group',)


class SubgroupAdmin(admin.ModelAdmin):
    list_display = ('group', 'name_subgroup', 'relations')
    list_display_links = ('group',)


class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('subgroup', 'start_schedule', 'end_schedule', 'file')
    list_display_links = ('subgroup',)


class LessonAdmin(admin.ModelAdmin):
    list_display = ('discipline', 'day', 'time', 'campus', 'audience', 'type', 'repetition',  'professor')
    list_display_links = ('discipline',)


class FileAdmin(admin.ModelAdmin):
    list_display = ('file_path',)
    list_display_links = ('file_path',)


class DivisionRelationsAdmin(admin.ModelAdmin):
    list_display = ('name_relations',)
    list_display_links = ('name_relations',)


class SpecialityAdmin(admin.ModelAdmin):
    list_display = ('cod_speciality', 'name_speciality')
    list_display_links = ('cod_speciality',)


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name_department', 'number_department', 'phone_department', 'email_department', 'head_department')
    list_display_links = ('name_department',)


class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('name_discipline',)
    list_display_links = ('name_discipline',)


class TypeAdmin(admin.ModelAdmin):
    list_display = ('name_type',)
    list_display_links = ('name_type',)


class RepetitionAdmin(admin.ModelAdmin):
    list_display = ('name_repetition',)
    list_display_links = ('name_repetition',)


class AudienceAdmin(admin.ModelAdmin):
    list_display = ('number_audience',)
    list_display_links = ('number_audience',)


class WeekAdmin(admin.ModelAdmin):
    list_display = ('day_of_week', 'day_reduction')
    list_display_links = ('day_of_week',)


class CampusAdmin(admin.ModelAdmin):
    list_display = ('name_campus', 'reduction', 'time_group')
    list_display_links = ('name_campus',)


class TimeGroupAdmin(admin.ModelAdmin):
    list_display = ('number_time_group',)
    list_display_links = ('number_time_group',)


class TimeAdmin(admin.ModelAdmin):
    list_display = ('time_group', 'number_lesson', 'time_start', 'time_end', 'time_out')
    list_display_links = ('number_lesson',)


# Register your models here.
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Professor, ProfessorAdmin)

admin.site.register(Group, GroupAdmin)
admin.site.register(Subgroup, SubgroupAdmin)
admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(Lesson, LessonAdmin)

admin.site.register(File, FileAdmin)
admin.site.register(DivisionRelations, DivisionRelationsAdmin)
admin.site.register(Speciality, SpecialityAdmin)
admin.site.register(Department, DepartmentAdmin)

admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(Type, TypeAdmin)
admin.site.register(Repetition, RepetitionAdmin)
admin.site.register(Audience, AudienceAdmin)

admin.site.register(Week, WeekAdmin)
admin.site.register(Campus, CampusAdmin)
admin.site.register(TimeGroup, TimeGroupAdmin)
admin.site.register(Time, TimeAdmin)
