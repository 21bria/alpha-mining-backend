from rest_framework import serializers
from geology.models import sampleCrmMralView

from rest_framework import serializers

class sampleCrmMralViewSerializer(serializers.ModelSerializer):

    class Meta:
        model = sampleCrmMralView
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
            'mral_ni',
            'mral_co',
            'mral_fe2o3',
            'mral_fe',
            'mral_mgo',
            'mral_sio2',
            'mral_al2o3',
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