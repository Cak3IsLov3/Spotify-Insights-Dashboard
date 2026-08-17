from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SpotifyImage:
    url: str
    height: int | None = None
    width: int | None = None


@dataclass
class UserProfile:
    id: str
    display_name: str | None = None
    email: str | None = None
    country: str | None = None
    product: str | None = None
    images: list[SpotifyImage] = field(default_factory=list)

    @property
    def avatar_url(self) -> str | None:
        return self.images[0].url if self.images else None

    @classmethod
    def from_dict(cls, data: dict) -> UserProfile:
        images = [SpotifyImage(**img) for img in data.get("images", [])]
        return cls(
            id=data["id"],
            display_name=data.get("display_name"),
            email=data.get("email"),
            country=data.get("country"),
            product=data.get("product"),
            images=images,
        )


@dataclass
class ArtistItem:
    id: str
    name: str
    genres: list[str] = field(default_factory=list)
    popularity: int = 0
    images: list[SpotifyImage] = field(default_factory=list)

    @property
    def image_url(self) -> str | None:
        return self.images[0].url if self.images else None

    @classmethod
    def from_dict(cls, data: dict) -> ArtistItem:
        images = [SpotifyImage(**img) for img in data.get("images", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            genres=data.get("genres", []),
            popularity=data.get("popularity", 0),
            images=images,
        )


@dataclass
class TrackArtist:
    id: str
    name: str


@dataclass
class TrackAlbum:
    id: str
    name: str
    images: list[SpotifyImage] = field(default_factory=list)

    @property
    def image_url(self) -> str | None:
        return self.images[0].url if self.images else None

    @classmethod
    def from_dict(cls, data: dict) -> TrackAlbum:
        images = [SpotifyImage(**img) for img in data.get("images", [])]
        return cls(id=data["id"], name=data["name"], images=images)


@dataclass
class TrackItem:
    id: str
    name: str
    artists: list[TrackArtist] = field(default_factory=list)
    album: TrackAlbum | None = None
    popularity: int = 0
    preview_url: str | None = None
    external_urls: dict[str, str] = field(default_factory=dict)

    @property
    def artist_names(self) -> str:
        return ", ".join(a.name for a in self.artists)

    @property
    def spotify_url(self) -> str | None:
        return self.external_urls.get("spotify")

    @classmethod
    def from_dict(cls, data: dict) -> TrackItem:
        artists = [
            TrackArtist(id=a.get("id", ""), name=a.get("name", ""))
            for a in data.get("artists", [])
        ]
        album_data = data.get("album")
        album = TrackAlbum.from_dict(album_data) if album_data else None
        return cls(
            id=data["id"],
            name=data["name"],
            artists=artists,
            album=album,
            popularity=data.get("popularity", 0),
            preview_url=data.get("preview_url"),
            external_urls=data.get("external_urls", {}),
        )


@dataclass
class GenreCount:
    name: str
    count: int
