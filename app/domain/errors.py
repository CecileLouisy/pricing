"""Erreurs métier du domaine Pricing.

Chaque erreur porte un code stable exposé aux consommateurs de l'API.
La couche adapters/api se charge de mapper chaque code sur un statut HTTP.
"""


class DomainError(Exception):
    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)


class ZoneNotFound(DomainError):
    code = "ZONE_NOT_FOUND"


class ModeNotFound(DomainError):
    code = "MODE_NOT_FOUND"


class QuoteNotFound(DomainError):
    code = "QUOTE_NOT_FOUND"


class GridNotFound(DomainError):
    code = "GRID_NOT_FOUND"


class InvalidDuration(DomainError):
    code = "INVALID_DURATION"


class InvalidMode(DomainError):
    code = "INVALID_MODE"


class InvalidRate(DomainError):
    code = "INVALID_RATE"


class InvalidFreePeriod(DomainError):
    code = "INVALID_FREE_PERIOD"


class RateAlreadyExists(DomainError):
    code = "RATE_ALREADY_EXISTS"


class Unauthorized(DomainError):
    code = "UNAUTHORIZED"
