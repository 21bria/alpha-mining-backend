from rest_framework import serializers
from geology.models import sampleDuplikatRoa

from rest_framework import serializers

class sampleDupRoaViewSerializer(serializers.ModelSerializer):

    class Meta:
        model = sampleDuplikatRoa
        fields = [
            'sample_number',
            'sample_method',
            'release_date',
            'sampling_deskripsi',
            'material',
            'ni',
            'co',
            'fe',
            'mgo',
            'sio2',

            'sample_original',
            'ni_ori',
            'co_ori',
            'fe_ori',
            'mgo_ori',
            'sio2_ori',

            'ni_diff',
            'co_diff',
            'fe_diff',
            'mgo_diff',
            'sio2_diff',

            'ni_rel_diff',
            'ni_rel_abs',
            'ni_error',

            'co_rel_diff',
            'co_rel_abs',
            'co_error',
            'fe_rel_diff',
            'fe_rel_abs',
            'fe_error',

            'mgo_rel_diff',
            'mgo_rel_abs',
            'mgo_error',

            'sio2_rel_diff',
            'sio2_rel_abs',
            'sio2_error',
            
            'iup_id',
            'iup_code',
            'iup_name'
        ]