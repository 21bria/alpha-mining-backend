from django.db import models

class SellingOfficialView(models.Model):
    id = models.IntegerField(primary_key=True)
    surveyor_id = models.IntegerField(null=True, blank=True)
    name_surveyor = models.CharField(max_length=255, null=True, blank=True)
    id_factory = models.IntegerField(null=True)
    factory_stock = models.CharField(max_length=200, null=True)

    type_selling = models.CharField(max_length=10)
    tonnage = models.FloatField(null=True)
    ni = models.FloatField(default=None, null=True, blank=True)
    co = models.FloatField(default=None, null=True, blank=True)
    al2o3 = models.FloatField(default=None, null=True, blank=True)
    cao = models.FloatField(default=None, null=True, blank=True)
    cr2o3 = models.FloatField(default=None, null=True, blank=True)
    fe = models.FloatField(default=None, null=True, blank=True)
    mgo = models.FloatField(default=None, null=True, blank=True)
    sio2 = models.FloatField(default=None, null=True, blank=True)
    mno = models.FloatField(default=None, null=True, blank=True)
    mc = models.FloatField(default=None, null=True, blank=True)

    so_number = models.CharField(max_length=100, null=True)
    product_code = models.CharField(max_length=100, null=True)
    barge_code = models.CharField(max_length=100, null=True)

    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)

    re_assay = models.IntegerField(null=True)
    # description = models.CharField(max_length=250, default=None, null=True, blank=True)

    user_id     = models.IntegerField(default=None, null=True, blank=True)
    username    = models.CharField(max_length=50,default=None, null=True, blank=True)
    iup_id      = models.IntegerField(default=None, null=True, blank=True)
    iup_code    = models.CharField(max_length=25,default=None, null=True, blank=True)
    iup_name    = models.CharField(max_length=50,default=None, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)


    class Meta:
        managed = False
        db_table = "view_selling_official"