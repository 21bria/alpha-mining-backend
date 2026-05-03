from rest_framework import serializers
from geology.models import sampleDuplikatMral

from rest_framework import serializers

class sampleDupMralViewSerializer(serializers.ModelSerializer):

   class Meta:
        model = sampleDuplikatMral
        fields = [
            'sample_number',
            'sample_method',
            'release_date',
            'sampling_deskripsi',
            'material',
            'ni',
            'co',
            'fe',
            'sio2',

            'sample_original',
            'ni_ori',
            'co_ori',
            'fe_ori',
            'sio2_ori',

            'ni_diff',
            'co_diff',
            'fe_diff',
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

            'sio2_rel_diff',
            'sio2_rel_abs',
            'sio2_error',
            
            'iup_id',
            'iup_code',
            'iup_name'
        ]