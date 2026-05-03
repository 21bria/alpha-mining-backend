from rest_framework import serializers
from master.models import MineGeologies

class MineGeologiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = MineGeologies
        fields = ["id", "name", "code", "status"]

    def validate_name(self, value: str):
        name = value.strip()

        qs = MineGeologies.objects.filter(name__iexact=name)

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("Nama Mine Geologies sudah ada.")

        return name

    def validate_code(self, value: str):
        code = value.strip().upper()  # 🔥 best practice: uppercase

        qs = MineGeologies.objects.filter(code__iexact=code)

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("Code sudah digunakan.")

        return code

    def validate(self, attrs):
        """
        Optional: validasi kombinasi field
        """
        name = attrs.get("name")
        code = attrs.get("code")

        if name and code:
            qs = MineGeologies.objects.filter(
                name__iexact=name.strip(),
                code__iexact=code.strip()
            )

            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    "Kombinasi name dan code sudah ada."
                )

        return attrs