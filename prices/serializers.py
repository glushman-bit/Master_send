from rest_framework import serializers

from .models import PriceTable


def normalize_cells(cells):
    rows = [[str(c) for c in row] for row in (cells or [])]
    if not rows:
        return [[]]
    width = max(len(row) for row in rows)
    return [row + [''] * (width - len(row)) for row in rows]


class PriceTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceTable
        fields = ['id', 'title', 'description', 'cells', 'order']


class PriceTableAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceTable
        fields = ['id', 'title', 'description', 'cells', 'order', 'is_published']

    def validate_cells(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Ячейки должны быть массивом строк.')
        for row in value:
            if not isinstance(row, list):
                raise serializers.ValidationError('Каждая строка должна быть массивом ячеек.')
        return value

    def create(self, validated_data):
        validated_data['cells'] = normalize_cells(validated_data.get('cells', []))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'cells' in validated_data:
            validated_data['cells'] = normalize_cells(validated_data.get('cells', []))
        return super().update(instance, validated_data)
