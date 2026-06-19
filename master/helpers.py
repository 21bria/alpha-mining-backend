
from django.db.models import Q
from master.models import SampleType

def user_default_iup_id(user):
    return getattr(user, "default_iup_id", None)

def user_allowed_iup_ids(user):
    ids = set(getattr(user, "allowed_iup_ids", None) or [])
    did = getattr(user, "default_iup_id", None)
    if did:
        ids.add(did)
    return list(ids)



def get_sample_types(
    is_production=False,
    is_geology=False,
    is_selling=False,
    is_monitoring=False,
):
    conditions = Q()

    if is_production:
        conditions |= Q(is_production=True)

    if is_geology:
        conditions |= Q(is_geology=True)

    if is_selling:
        conditions |= Q(is_selling=True)

    if is_monitoring:
        conditions |= Q(is_monitoring=True)

    if not conditions:
        return []

    return list(
        SampleType.objects
        .filter(conditions, status=1)
        .values_list("type_sample", flat=True)
    )