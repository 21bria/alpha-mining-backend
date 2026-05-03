from rest_framework import serializers
from geology.models import sampleCrmRoaView

from rest_framework import serializers

class sampleCrmRoaViewSerializer(serializers.ModelSerializer):

    class Meta:
        model = sampleCrmRoaView
        fields = [
            'oreas_name',
            'ni',
            'co',
            'fe2o3',
            'fe',
            'mgo',
            'sio2',
            'al2o3',
            'sample_number',
            'sampling_deskripsi',
            'sample_id',
            'release_date',
            'roa_ni',
            'roa_co',
            'roa_fe2o3',
            'roa_fe',
            'roa_mgo',
            'roa_sio2',
            'roa_al2o3',
            'diff_ni',
            'diff_co',
            'diff_fe2o3',
            'diff_fe',
            'diff_mgo',
            'diff_sio2',
            'diff_al2o3',
            'iup_id',
            'iup_code',
            'iup_name',
        ]