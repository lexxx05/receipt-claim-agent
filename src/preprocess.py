import json
from dataclasses import dataclass
from pathlib import Path

# === PARAMETER ===
MIN_SCORE = 0.5 # token dengan CONFIDENCE SCORE < 0.5 akan dibuang
MIN_OVERLAP = 0.5 # 2 token sebaris yang tumpang tindih vertikalnya >= 50% tinggi kotak lebih pendek
SEPARATOR = " | " # pemisah antara token token dalam 1 baris. contoh: "1 REAL GANACHE | 16,500"

#########################################################
# Pydantic Bentuk Data -> 1 token = 1 potongan teks OCR #
#########################################################
@dataclass # otomatis bikin init, jadi bisa tulis Token("16,500", 0.99, (577, 548, 664, 585))
class Token:
    text: str 
    score: float # confidence score
    box: tuple[float, float, float, float] # (x1, y1, x2, y2)

    @property # decorator ini bikin methodnya bisa dipanggil kayak atribut: token.top -> tanpa tanda kurung
    def top(self) -> float:
        return self.box[1] # top = y1

    @property
    def bottom(self) -> float:
        return self.box[3] # bottom = y2

    @property
    def left(self) -> float:
        return self.box[0] # left = x1

    @property
    def center_y(self) -> float:
        return (self.box[1] + self.box[3]) / 2 # centroid vertical

############################################################
# Baca cache OCR paddle -- (convert jadi) --> daftar token #
############################################################
def load_ocr_tokens(path: Path) -> list[Token]:
    """
    Function ini buat CONVERT seluruh hasil ocr -> LIST CLASS TOKEN(text, scores, bbox)
    Cuman function ini yang tau format paddle, yang lain cuman trima list[Token]
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Token(text=text, score=float(score), box=tuple(box))
        for text, score, box in zip(data['rec_texts'], data['rec_scores'], data['rec_boxes'])
    ]

###############################################
# Buang Token yang Skornya RENDAH atau KOSONG #
###############################################
def filter_tokens(tokens: list[Token], min_score: float = MIN_SCORE) -> list[Token]:
    """
    contoh struk 0000: Token("Jmunn", 0.44, ...) dibuang (0.44 < 0.5)
    t.text.strip() -> "" untuk teks kosong/spasi saja -> dianggep false dan dibuang
    """
    return [t for t in tokens if t.score >= min_score and t.text.strip()]

#####################################
# Hitung Overlap Vertical 2 Rentang #
#####################################
def _vertical_overlap(top_a: float, bottom_a: float, top_b: float, bottom_b: float) -> float:
    """
    Outputnya adalah ratio overlap HEIGHT terhadap height yang lebih pendek 
    dari 2 token di baris yang berbeda tapi berdekatan (biar dianggap 1 baris)
    TUJUANNYA: buat bedain mana token yang sebaris dan mana yang beda baris (nentuin threshold)

    logikanya, bakal ada 2 token '16.500' (top = 548, bottom = 585) 
    dan '1 GANACHE' (top = 551, bottom = 587) -> GANACHE posisinya ada dibawah 16.500
    - hitung overlap di heightnya: ngurangin yang posisinya lebih atas dari buttom -> min(bottom_a, bottom_b)
      dengan yang lebih bawah dari top --> max(top_a, top_b)
      INGAT, y semakin bawah semakin gede, semakin atas semakin kecil
    - hitung tinggi kotak (height) yang lebih pendek
    - bagi antara overlap dengan tinggi kotak yg lebih pendek
    """
    overlap = min(bottom_a, bottom_b) - max(top_a, top_b) # tinggi dari overlap
    shorter = min(bottom_a - top_a, bottom_b - top_b) # tinggi rentang kotak yang lebih pendek
    if shorter <= 0: # kotak tanpa tinggi -> ANGGAP tidak sebaris
        return 0.0
    return max(overlap, 0) / shorter

###################################
# TOKEN --(dikelompokin)--> BARIS #
###################################
def group_lines(tokens: list[Token], min_overlap: float = MIN_OVERLAP) -> list[list[Token]]:
    lines: list[list[Token]] = [] # tiap elemen -> 1 baris -> list dri token

    for token in sorted(tokens, key= lambda t: t.center_y): # sorting keseluruhan token
        for line in lines: # cek baris yg udah ada one by one
            line_top = sum(t.top for t in line) / len(line) # rata rata y atas token" di baris itu
            line_bottom = sum(t.bottom for t in line) / len(line) # rata rata y bawah dari token"
            if _vertical_overlap(token.top, token.bottom, line_top, line_bottom) >= min_overlap:
                line.append(token) # cukup bertumpuk -> append di object ini
                break
        else:
            lines.append([token]) # tidak cocok dengan baris manapun -> baris baru

    for line in lines:
        line.sort(key = lambda t: t.left) # dalam 1 baris HARUS urut dari kiri ke kanan

    lines.sort(key = lambda line: sum(t.center_y for t in line) / len(line)) # baris baris itu HARUS urut dari atas ke bawah
    
    return lines

################################################
# WRAP semuanya jadi TEKS untuk DIKIRIM KE LLM #
################################################
def build_text(
    tokens: list[Token],
    min_score: float = MIN_SCORE,
    min_overlap: float = MIN_OVERLAP,
    separator: str = SEPARATOR,
):
    # langkah 1: buang token yg lemah (confident score)
    kept = filter_tokens(tokens, min_score)

    # langkah 2: susun token jadi baris based on overlap rule
    lines = group_lines(kept, min_overlap)

    return "\n".join(separator.join(t.text for t in line) for line in lines)