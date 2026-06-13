from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from selling.models import SellingBarging, DomeTransfer
from master.models import SourceMinesDome


def get_tonnage_by_dome(dome_id: int) -> Decimal:
    result = (
        SellingBarging.objects
        .filter(id_pile=dome_id)
        .aggregate(total=Sum("tonnage"))
    )
    total = result["total"]
    if total is None:
        return Decimal("0")
    return Decimal(str(total))


def build_transfer_ref(original_dome_id: int, target_dome_id: int) -> str:
    ts = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"TRF-{original_dome_id}-{target_dome_id}-{ts}"


@transaction.atomic
def transfer_dome_selling(original_dome_id: int, target_dome_id: int, ref_id: str):
    if original_dome_id == target_dome_id:
        raise ValueError("Original dome dan target dome tidak boleh sama.")

    original_total = get_tonnage_by_dome(original_dome_id)
    target_total = get_tonnage_by_dome(target_dome_id)

    if original_total <= Decimal("0"):
        raise ValueError("Original dome tidak punya tonnage selling untuk di-transfer.")

    # RULE BARU: target dome wajib sudah punya selling
    if target_total <= Decimal("0"):
        raise ValueError("Target dome belum punya selling, tidak bisa dilakukan compositing.")


    # pindahkan semua selling source ke target
    updated_count = SellingBarging.objects.filter(id_pile=original_dome_id).update(
        id_pile=target_dome_id,
        pile_original=original_dome_id,
        dome_compositing=ref_id,
    )

    return {
        "original_total": original_total,
        "target_total": target_total,
        "updated_count": updated_count,
    }

@transaction.atomic
def undo_dome_transfer(transfer_obj: DomeTransfer, user=None, notes=None):
    if transfer_obj.is_undone or transfer_obj.status == "UNDONE":
        raise ValueError("Merge ini sudah di-undo.")

    qs = SellingBarging.objects.filter(dome_compositing=transfer_obj.ref_id)

    if not qs.exists():
        raise ValueError("Tidak ada data produksi yang terkait dengan merge ini.")

    objs = []
    for obj in qs:
        if obj.pile_original:
            obj.id_pile = obj.pile_original
            obj.pile_original = None
            obj.dome_compositing = None
            objs.append(obj)

    if objs:
        SellingBarging.objects.bulk_update(
            objs,
            ["id_pile", "pile_original", "dome_compositing"]
        )

    transfer_obj.status = "UNDONE"
    transfer_obj.is_undone = True
    transfer_obj.undone_at = timezone.now()
    transfer_obj.undone_by = user
    transfer_obj.undo_notes = notes
    transfer_obj.save(update_fields=[
        "status",
        "is_undone",
        "undone_at",
        "undone_by",
        "undo_notes",
    ])

    return transfer_obj