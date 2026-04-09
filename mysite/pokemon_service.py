from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


POKEAPI_BASE = "https://pokeapi.co/api/v2"
POKEAPI_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "RazberryFaceDemo/1.0 (+local Django app; contact: local-dev)",
}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PokemonChoice:
    slug: str
    label: str
    comment: str
    local_image_url: str


YOUTHFUL_CHOICES = (
    PokemonChoice("pikachu", "ピカチュウ", "明るく親しみやすい雰囲気", "/static/pokemon/pikachu.svg"),
    PokemonChoice("togepi", "トゲピー", "やさしく柔らかな雰囲気", "/static/pokemon/togepi.svg"),
    PokemonChoice("eevee", "イーブイ", "素直で親しみやすい雰囲気", "/static/pokemon/eevee.svg"),
    PokemonChoice("pichu", "ピチュー", "無邪気で元気な雰囲気", ""),
    PokemonChoice("mew", "ミュウ", "自由で愛らしい雰囲気", ""),
    PokemonChoice("jirachi", "ジラーチ", "きらっとした多幸感のある雰囲気", ""),
    PokemonChoice("minun", "マイナン", "朗らかで親しみやすい雰囲気", ""),
    PokemonChoice("plusle", "プラスル", "はつらつとした前向きな雰囲気", ""),
)

CALM_CHOICES = (
    PokemonChoice("snorlax", "カビゴン", "おだやかで包容力のある雰囲気", "/static/pokemon/snorlax.svg"),
    PokemonChoice("lapras", "ラプラス", "落ち着きと安心感がある雰囲気", ""),
    PokemonChoice("dragonair", "ハクリュー", "しなやかで気品のある雰囲気", ""),
    PokemonChoice("vaporeon", "シャワーズ", "やわらかく涼しげな雰囲気", ""),
    PokemonChoice("meganium", "メガニウム", "やさしく穏やかな雰囲気", ""),
    PokemonChoice("slowpoke", "ヤドン", "ゆったりした癒やし系の雰囲気", ""),
    PokemonChoice("furret", "オオタチ", "のんびり親しみやすい雰囲気", ""),
    PokemonChoice("altaria", "チルタリス", "ふんわり上品な雰囲気", ""),
)

CUTE_CHOICES = (
    PokemonChoice("jigglypuff", "プリン", "やわらかく愛嬌のある雰囲気", "/static/pokemon/jigglypuff.svg"),
    PokemonChoice("clefairy", "ピッピ", "チャーミングで可愛らしい雰囲気", ""),
    PokemonChoice("skitty", "エネコ", "人なつっこく可憐な雰囲気", ""),
    PokemonChoice("teddiursa", "ヒメグマ", "ころんと愛らしい雰囲気", ""),
    PokemonChoice("mareep", "メリープ", "ふわっとした優しい雰囲気", ""),
    PokemonChoice("sylveon", "ニンフィア", "華やかで柔らかな雰囲気", ""),
    PokemonChoice("chikorita", "チコリータ", "素朴でやさしい雰囲気", ""),
    PokemonChoice("happiny", "ピンプク", "ほんわかした親近感のある雰囲気", ""),
)

SHARP_CHOICES = (
    PokemonChoice("lucario", "ルカリオ", "シャープで凛とした雰囲気", "/static/pokemon/lucario.svg"),
    PokemonChoice("absol", "アブソル", "クールで研ぎ澄まされた雰囲気", ""),
    PokemonChoice("zoroark", "ゾロアーク", "ミステリアスで華のある雰囲気", ""),
    PokemonChoice("sneasel", "ニューラ", "すばやく鋭い雰囲気", ""),
    PokemonChoice("greninja", "ゲッコウガ", "切れ味のあるスマートな雰囲気", ""),
    PokemonChoice("scyther", "ストライク", "精悍でシャープな雰囲気", ""),
    PokemonChoice("gallade", "エルレイド", "端正でスマートな雰囲気", ""),
    PokemonChoice("umbreon", "ブラッキー", "静かでクールな存在感がある雰囲気", ""),
)

BALANCED_CHOICES = (
    PokemonChoice("dragonite", "カイリュー", "存在感があって頼もしそうな雰囲気", "/static/pokemon/dragonite.svg"),
    PokemonChoice("charizard", "リザードン", "パワフルで華のある雰囲気", ""),
    PokemonChoice("arcanine", "ウインディ", "堂々として頼もしげな雰囲気", ""),
    PokemonChoice("garchomp", "ガブリアス", "迫力と安定感をあわせ持つ雰囲気", ""),
    PokemonChoice("blaziken", "バシャーモ", "熱量があってキレのある雰囲気", ""),
    PokemonChoice("tyranitar", "バンギラス", "重厚で揺るがない雰囲気", ""),
    PokemonChoice("salamence", "ボーマンダ", "ダイナミックで力強い雰囲気", ""),
    PokemonChoice("aggron", "ボスゴドラ", "どっしり頼れる雰囲気", ""),
)


class PokemonService:
    def recommend(self, *, age: int | None, bbox: list[int], image_shape, matched_name: str | None) -> dict | None:
        choice = self._select_choice(age=age, bbox=bbox, image_shape=image_shape, matched_name=matched_name)
        pokemon_data, pokemon_error = self._fetch_pokemon_payload(choice.slug)
        if pokemon_data is None:
            return {
                "name": choice.label,
                "slug": choice.slug,
                "types": [],
                "image_url": choice.local_image_url,
                "comment": self._build_comment(choice.comment, matched_name),
                "source": "local-fallback",
                "source_detail": pokemon_error or "PokeAPI response was empty.",
            }

        species_data, species_error = self._fetch_species_payload(pokemon_data.get("species", {}).get("url", ""))
        japanese_name = self._extract_japanese_name(species_data) or choice.label
        image_url = self._extract_artwork_url(pokemon_data) or choice.local_image_url
        return {
            "name": japanese_name,
            "slug": choice.slug,
            "types": [entry["type"]["name"] for entry in pokemon_data.get("types", [])],
            "image_url": image_url,
            "comment": self._build_comment(choice.comment, matched_name),
            "source": "pokeapi",
            "source_detail": species_error or "",
        }

    def _select_choice(
        self,
        *,
        age: int | None,
        bbox: list[int],
        image_shape,
        matched_name: str | None,
    ) -> PokemonChoice:
        image_height, image_width = image_shape[:2]
        face_width = max(1, bbox[2] - bbox[0])
        face_height = max(1, bbox[3] - bbox[1])
        face_ratio = face_width / face_height
        face_area_ratio = (face_width * face_height) / max(1, image_width * image_height)
        seed = self._build_seed(
            age=age,
            face_width=face_width,
            face_height=face_height,
            face_ratio=face_ratio,
            face_area_ratio=face_area_ratio,
            matched_name=matched_name,
        )

        if age is not None and age <= 18:
            return YOUTHFUL_CHOICES[seed % len(YOUTHFUL_CHOICES)]
        if age is not None and age >= 38 and face_area_ratio > 0.18:
            return CALM_CHOICES[seed % len(CALM_CHOICES)]
        if face_ratio >= 0.92:
            return CUTE_CHOICES[seed % len(CUTE_CHOICES)]
        if face_ratio <= 0.74:
            return SHARP_CHOICES[seed % len(SHARP_CHOICES)]
        if age is not None and age >= 28:
            return CALM_CHOICES[seed % len(CALM_CHOICES)]
        return BALANCED_CHOICES[seed % len(BALANCED_CHOICES)]

    @staticmethod
    def _build_seed(
        *,
        age: int | None,
        face_width: int,
        face_height: int,
        face_ratio: float,
        face_area_ratio: float,
        matched_name: str | None,
    ) -> int:
        name_value = sum(ord(char) for char in matched_name or "")
        age_value = age or 0
        return (
            name_value
            + age_value * 17
            + face_width * 11
            + face_height * 7
            + int(face_ratio * 1000)
            + int(face_area_ratio * 10000)
        )

    @staticmethod
    def _build_comment(base_comment: str, matched_name: str | None) -> str:
        if matched_name:
            return f"{matched_name}さんは、{base_comment}です。"
        return f"{base_comment}が伝わるので、このポケモンを選びました。"

    @staticmethod
    def _extract_artwork_url(pokemon_data: dict) -> str:
        artwork = (
            pokemon_data.get("sprites", {})
            .get("other", {})
            .get("official-artwork", {})
            .get("front_default")
        )
        if artwork:
            return artwork
        return pokemon_data.get("sprites", {}).get("front_default", "")

    @staticmethod
    def _extract_japanese_name(species_data: dict | None) -> str | None:
        if not species_data:
            return None
        for entry in species_data.get("names", []):
            if entry.get("language", {}).get("name") == "ja-Hrkt":
                return entry.get("name")
        for entry in species_data.get("names", []):
            if entry.get("language", {}).get("name") == "ja":
                return entry.get("name")
        return None

    @staticmethod
    @lru_cache(maxsize=64)
    def _fetch_json(url: str) -> tuple[dict | None, str | None]:
        if not url:
            return None, "URL was empty."
        try:
            request = Request(url, headers=POKEAPI_HEADERS)
            with urlopen(request, timeout=5) as response:
                return json.load(response), None
        except HTTPError as error:
            detail = f"HTTP {error.code} while requesting {url}: {error.reason}"
            logger.warning(detail)
            return None, detail
        except URLError as error:
            reason = getattr(error, "reason", error)
            detail = f"Network error while requesting {url}: {reason}"
            logger.warning(detail)
            return None, detail
        except TimeoutError as error:
            detail = f"Timed out while requesting {url}: {error}"
            logger.warning(detail)
            return None, detail
        except ValueError as error:
            detail = f"Invalid JSON returned from {url}: {error}"
            logger.warning(detail)
            return None, detail

    def _fetch_pokemon_payload(self, slug: str) -> tuple[dict | None, str | None]:
        return self._fetch_json(f"{POKEAPI_BASE}/pokemon/{slug}")

    def _fetch_species_payload(self, url: str) -> tuple[dict | None, str | None]:
        return self._fetch_json(url)


def get_pokemon_service() -> PokemonService:
    return PokemonService()
