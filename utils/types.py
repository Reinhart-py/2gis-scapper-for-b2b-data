from dataclasses import dataclass
from typing import List, Literal, TypeAlias

StrOrNull: TypeAlias = str | Literal["null"]
DataList: TypeAlias = List[StrOrNull]


@dataclass
class ColumnData:
    title: DataList
    phone_1: DataList
    phone_2: DataList
    phone_3: DataList
    address: DataList