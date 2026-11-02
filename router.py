import re

CODE_RE = re.compile(
    r"(\bdef |\bclass |\bimport |\btraceback\b|\bexception\b|\berror\b|\bbug\b|\bdebug\b|"
    r"\bkode\b|\bcode\b|\bcoding\b|\bscript\b|\bskrip\b|\bprogram\b|\bprogramming\b|"
    r"\bfunction\b|\bfungsi\b|\bvariabel\b|\bvariable\b|\bmethod\b|\bcompile\b|"
    r"\bpython\b|\bjavascript\b|\btypescript\b|\bjava\b|\bkotlin\b|\bphp\b|\bgolang\b|"
    r"\bsql\b|\bdatabase\b|\bbash\b|\bshell\b|\bterminal\b|\bcommand\b|\blinux\b|"
    r"\bhtml\b|\bcss\b|\breact\b|\bnode\b|\bnpm\b|\bpip\b|\bdocker\b|\bgit\b|"
    r"\bapi\b|\bjson\b|\bregex\b|\brefactor\b|"
    r"\.py\b|\.js\b|\.ts\b|\.html\b|"
    r"```)",
    re.IGNORECASE,
)

HOMEWORK_RE = re.compile(
    r"(\btugas\b|\bpr\b|\brumus\b|\bhitung\b|\bjelaskan\b|\bmatematika\b|\bfisika\b|"
    r"\bkimia\b|\bbiologi\b|\bsejarah\b|\bgeografi\b|\bekonomi\b|\bsosiologi\b|"
    r"\besai\b|\bessay\b|\bhomework\b|\blatihan\b|\bkuis\b|\bujian\b|\bulangan\b|"
    r"\bpelajaran\b|\bsekolah\b|\bkuliah\b|\bmateri\b|\bpembahasan\b|"
    r"\bpersamaan\b|\bintegral\b|\bturunan\b|\baljabar\b|\bpecahan\b|\bkalkulus\b|"
    r"\b(soal latihan|soal ujian|soal matematika|kerjakan soal|jawab soal|contoh soal)\b)",
    re.IGNORECASE,
)

WEB_RE = re.compile(
    r"(\b(cari|carikan|search|berita|terbaru|terkini|harga|hari ini|cuaca|kurs|"
    r"skor|jadwal|rilis|trending|viral|saham|bitcoin)\b|https?://)",
    re.IGNORECASE,
)


def route(prompt: str, override: str | None = None) -> str:
    """Pilih mode. Override dari /mode mengalahkan deteksi otomatis."""
    if override:
        return override
    if CODE_RE.search(prompt):
        return "code"
    if HOMEWORK_RE.search(prompt):
        return "homework"
    return "chat"


def needs_web(prompt: str) -> bool:
    return bool(WEB_RE.search(prompt))
