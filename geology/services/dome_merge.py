from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from geology.models import OreProductions, DomeMerge
from master.models import SourceMinesDome


def get_tonnage_by_dome(dome_id: int) -> Decimal:
    result = (
        OreProductions.objects
        .filter(id_pile=dome_id)
        .aggregate(total=Sum("tonnage"))
    )
    total = result["total"]
    if total is None:
        return Decimal("0")
    return Decimal(str(total))


def build_merge_ref(original_dome_id: int, target_dome_id: int) -> str:
    ts = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"MRG-{original_dome_id}-{target_dome_id}-{ts}"


@transaction.atomic
def merge_dome_productions(original_dome_id: int, target_dome_id: int, ref_id: str):
    if original_dome_id == target_dome_id:
        raise ValueError("Original dome dan target dome tidak boleh sama.")

    original_total = get_tonnage_by_dome(original_dome_id)
    target_total = get_tonnage_by_dome(target_dome_id)

    if original_total <= Decimal("0"):
        raise ValueError("Original dome tidak punya tonnage produksi untuk di-merge.")

    # RULE BARU: target dome wajib sudah punya produksi
    if target_total <= Decimal("0"):
        raise ValueError("Target dome belum punya produksi, tidak bisa dilakukan compositing.")

    # cegah source dome yang sudah pernah di-merge dan belum di-undo
    source_dome = SourceMinesDome.objects.filter(id=original_dome_id).first()
    if source_dome and getattr(source_dome, "compositing", None) == "Yes":
        raise ValueError("Original dome sudah pernah di-compositing dan belum di-undo.")

    # pindahkan semua produksi source ke target
    updated_count = OreProductions.objects.filter(id_pile=original_dome_id).update(
        id_pile=target_dome_id,
        pile_original=original_dome_id,
        dome_compositing=ref_id,
    )

    SourceMinesDome.objects.filter(id=original_dome_id).update(compositing="Yes")

    return {
        "original_total": original_total,
        "target_total": target_total,
        "updated_count": updated_count,
    }


@transaction.atomic
def undo_dome_merge(merge_obj: DomeMerge, user=None, notes=None):
    if merge_obj.is_undone or merge_obj.status == "UNDONE":
        raise ValueError("Merge ini sudah di-undo.")

    qs = OreProductions.objects.filter(dome_compositing=merge_obj.ref_id)

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
        OreProductions.objects.bulk_update(
            objs,
            ["id_pile", "pile_original", "dome_compositing"]
        )

    SourceMinesDome.objects.filter(id=merge_obj.original_dome_id).update(compositing="No")

    merge_obj.status = "UNDONE"
    merge_obj.is_undone = True
    merge_obj.undone_at = timezone.now()
    merge_obj.undone_by = user
    merge_obj.undo_notes = notes
    merge_obj.save(update_fields=[
        "status",
        "is_undone",
        "undone_at",
        "undone_by",
        "undo_notes",
    ])

    return merge_obj