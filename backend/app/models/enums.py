from enum import Enum


class TransactionType(str, Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"


class PaidBy(str, Enum):
    EU = "eu"
    PARCEIRA = "parceira"
    AMBOS = "ambos"


class SplitType(str, Enum):
    HALF = "50/50"
    FULL_USER1 = "100_user1"
    FULL_USER2 = "100_user2"
    CUSTOM = "custom"
