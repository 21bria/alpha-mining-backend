from rest_framework import serializers
from master.models import StockFactories

class StockFactoriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockFactories
        fields = ["id", "factory_stock", "description","capacity","status","user"]
        read_only_fields = ["user"]

    def validate_factory_stock(self, value: str):
        factory_stock = value.strip()
        qs = StockFactories.objects.filter(factory_stock__iexact=factory_stock)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Nama sudah ada.")
        return factory_stock
    
    def create(self, validated_data):
        # print("USER LOGIN:", self.context["request"].user)
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)