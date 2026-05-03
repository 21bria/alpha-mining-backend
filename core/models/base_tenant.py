from .base import IUPCodeModel
from .soft_delete import SoftDeleteModel

class BaseTenantModel(IUPCodeModel, SoftDeleteModel):
    class Meta:
        abstract = True