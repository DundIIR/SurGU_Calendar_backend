from rest_framework import serializers

from .create_json import create_json
from .models import *

# Сериализатор для списка групп
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['number_group']


# Сериализатор для расписания
class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'

    def to_representation(self, instance):
        request = self.context.get('request')
        shorten_names = request.GET.get('shorten_names', 'false').lower() == 'true'
        return create_json(instance, shorten_names)


# Сериализатор для групп
class SubgroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subgroup
        fields = '__all__'

    def to_representation(self, instance):
        return {
            'subgroup': instance.name_subgroup,
            'group': instance.group.number_group
        }

#


# Сериализатор для преподавателей
class ProfessorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Professor
        fields = []

    def to_representation(self, instance):
        return {
            'full_name': f"{instance.last_name} {instance.first_name} {instance.patronymic}"
        }


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'is_active', 'role']

    def to_representation(self, instance):
        role = instance.role.name if instance.role else "Роль не указана"
        return {
            'message': 'Все хорошо, пользователь авторизован',
            'email': instance.email,
            'is_active': instance.is_active,
            'role': role
        }


class UserListSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'role']


class FileSerializer(serializers.ModelSerializer):

    class Meta:
        model = FileSchedule
        fields = ['id', 'file_name', 'file_url']

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'name': instance.file_name,
            'url': instance.file_url
        }