from rest_framework import serializers
from selling.models import SellingOfficialView,SellingOfficial
from rest_framework import serializers

class SellingOfficialSerializer(serializers.ModelSerializer):

    surveyor_name = serializers.CharField(source="master.Surveyor", read_only=True)
    factory_name = serializers.SerializerMethodField()
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = SellingOfficial
        fields = [
            "id",
            "surveyor",
            "surveyor_name",
            "type_selling",
            "tonnage",
            "id_factory",
            "factory_name",
            "so_number",
            "product_code",
            "barge_code",
            "official",
            "ni",
            "co",
            "start_date",
            "end_date",
            "description",
            "re_assay",
            "user",
        ]
        
class SellingOfficialViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellingOfficialView
        fields = [
            "id",
            "iup_id", "iup_code", "iup_name",
            "name_surveyor",
            "type_selling",
            "tonnage",
            "id_factory",
            "factory_stock",
            "so_number",
            "product_code",
            "barge_code",
            "ni",
            "co",
            "al2o3",
            "cao",
            "cr2o3",
            "fe",
            "mgo",
            "sio2",
            "mno",
            "mc",
            "start_date",
            "end_date",
            # "description",
            "re_assay",
            "user_id",
            "username",
            "created_at",
        ]