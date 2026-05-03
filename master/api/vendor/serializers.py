from rest_framework import serializers
from master.models import Vendors

class VendorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendors
        fields = ["id","code","vendor_name","status","description"]

    def validate_vendor_name(self, value: str):
        vendor_name = value.strip()
        qs = Vendors.objects.filter(vendor_name__iexact=vendor_name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Nama Vendor sudah ada.")
        return vendor_name
