"""Exact rational and sparse-polynomial observables alongside Signal8 outputs."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from math import prod
from typing import Iterable, Mapping, Sequence

class ExactValueError(ValueError):
    """Invalid exact scalar, polynomial, or observation frame."""

def _fraction(value):
    if isinstance(value, bool) or isinstance(value, float):
        raise ExactValueError("use an integer, Fraction, or integer pair for exact rationals")
    try:
        if isinstance(value, tuple) and len(value) == 2:
            numerator, denominator = value
            if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
                raise ExactValueError("rational pair must contain two integers")
            return Fraction(numerator, denominator)
        return Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ExactValueError(f"invalid rational value: {exc}") from exc

@dataclass(frozen=True, slots=True)
class RationalValue:
    value: Fraction
    def __post_init__(self):
        object.__setattr__(self, "value", _fraction(self.value))
    @classmethod
    def of(cls, numerator: int, denominator: int = 1):
        if isinstance(numerator, bool) or isinstance(denominator, bool):
            raise ExactValueError("numerator and denominator must be integers")
        try:
            return cls(Fraction(numerator, denominator))
        except (ValueError, ZeroDivisionError) as exc:
            raise ExactValueError(f"invalid rational value: {exc}") from exc
    @property
    def numerator(self): return self.value.numerator
    @property
    def denominator(self): return self.value.denominator
    def to_dict(self):
        return {"type":"rational","numerator":self.numerator,"denominator":self.denominator}
    def __add__(self, other):
        if not isinstance(other, RationalValue): return NotImplemented
        return RationalValue(self.value + other.value)
    def __sub__(self, other):
        if not isinstance(other, RationalValue): return NotImplemented
        return RationalValue(self.value - other.value)
    def __mul__(self, other):
        if not isinstance(other, RationalValue): return NotImplemented
        return RationalValue(self.value * other.value)
    def __truediv__(self, other):
        if not isinstance(other, RationalValue): return NotImplemented
        return RationalValue(self.value / other.value)

@dataclass(frozen=True, slots=True)
class ExactPolynomial:
    """Sparse multivariate polynomial over exact rational coefficients."""
    variables: tuple[str, ...]
    terms: tuple[tuple[tuple[int, ...], Fraction], ...]
    def __post_init__(self):
        variables = tuple(self.variables)
        if len(set(variables)) != len(variables) or any(not isinstance(x,str) or not x for x in variables):
            raise ExactValueError("variables must be unique non-empty names")
        combined = {}
        for powers, coefficient in self.terms:
            powers = tuple(powers)
            if len(powers) != len(variables):
                raise ExactValueError("monomial degree vector must match variables")
            if any(isinstance(x,bool) or not isinstance(x,int) or x < 0 for x in powers):
                raise ExactValueError("monomial exponents must be non-negative integers")
            coefficient = _fraction(coefficient)
            combined[powers] = combined.get(powers,Fraction(0)) + coefficient
        object.__setattr__(self,"variables",variables)
        object.__setattr__(self,"terms",tuple(
            (powers,coefficient) for powers,coefficient in sorted(combined.items()) if coefficient
        ))
    @classmethod
    def constant(cls, value, variables=()):
        variables=tuple(variables); coefficient=_fraction(value)
        return cls(variables,((((0,)*len(variables)),coefficient),) if coefficient else ())
    @classmethod
    def variable(cls, name, variables):
        variables=tuple(variables)
        if name not in variables: raise ExactValueError(f"variable {name!r} is outside schema")
        return cls(variables,((tuple(1 if item==name else 0 for item in variables),Fraction(1)),))
    @property
    def total_degree(self):
        return max((sum(powers) for powers,_ in self.terms),default=0)
    def _check(self,other):
        if not isinstance(other,ExactPolynomial) or self.variables!=other.variables:
            raise ExactValueError("polynomials must use the same ordered variable schema")
    def __add__(self,other):
        self._check(other); return ExactPolynomial(self.variables,self.terms+other.terms)
    def __sub__(self,other):
        self._check(other)
        return ExactPolynomial(self.variables,self.terms+tuple((p,-c) for p,c in other.terms))
    def __mul__(self,other):
        self._check(other); terms=[]
        for p,c in self.terms:
            for q,d in other.terms:
                terms.append((tuple(a+b for a,b in zip(p,q)),c*d))
        return ExactPolynomial(self.variables,tuple(terms))
    def evaluate(self, values: Mapping[str, Fraction | int]):
        if set(values)!=set(self.variables):
            raise ExactValueError("evaluation must supply exactly the polynomial variable schema")
        resolved={key:_fraction(value) for key,value in values.items()}
        total=Fraction(0)
        for powers,coefficient in self.terms:
            total += coefficient*prod(resolved[name]**power for name,power in zip(self.variables,powers))
        return RationalValue(total)
    def to_dict(self):
        return {"type":"polynomial","variables":list(self.variables),"terms":[
            {"powers":list(p),"coefficient":{"numerator":c.numerator,"denominator":c.denominator}}
            for p,c in self.terms
        ]}

@dataclass(frozen=True, slots=True)
class ExactObservable:
    """A typed exact measurement kept outside finite Signal8 output channels."""
    name: str
    value: RationalValue | ExactPolynomial
    unit: str = "dimensionless"
    source_ref: str = ""
    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name: raise ExactValueError("observable name is required")
        if not isinstance(self.value,(RationalValue,ExactPolynomial)): raise ExactValueError("invalid exact observable type")
        if not isinstance(self.unit,str) or not self.unit: raise ExactValueError("observable unit is required")
    def to_dict(self):
        return {"name":self.name,"value":self.value.to_dict(),"unit":self.unit,"source_ref":self.source_ref}

@dataclass(frozen=True, slots=True)
class ExactObservableFrame:
    """Exact observables attached to a logical state without narrowing to Signal8."""
    state_id: str
    clock_id: str
    logical_tick: int
    ground_fingerprint: str
    observables: tuple[ExactObservable,...]
    def __post_init__(self):
        if not self.state_id or not self.clock_id or not self.ground_fingerprint:
            raise ExactValueError("state, clock and Ground fingerprint are required")
        if isinstance(self.logical_tick,bool) or not isinstance(self.logical_tick,int) or self.logical_tick<0:
            raise ExactValueError("logical_tick must be a non-negative integer")
        values=tuple(self.observables)
        if any(not isinstance(x,ExactObservable) for x in values) or len({x.name for x in values})!=len(values):
            raise ExactValueError("observables must be uniquely named ExactObservable values")
        object.__setattr__(self,"observables",values)
    def to_dict(self):
        return {"format":"VGI-ExactObservableFrame-1","state_id":self.state_id,
                "clock_id":self.clock_id,"logical_tick":self.logical_tick,
                "ground_fingerprint":self.ground_fingerprint,
                "observables":[item.to_dict() for item in self.observables]}

def rational_sum(values: Iterable[Fraction | int]):
    return RationalValue(sum((_fraction(x) for x in values),Fraction(0)))

def rational_mean(values: Sequence[Fraction | int]):
    if not values: raise ExactValueError("mean requires at least one value")
    return RationalValue(sum((_fraction(x) for x in values),Fraction(0))/len(values))

def rational_variance(values: Sequence[Fraction | int], *, sample=False):
    if not values: raise ExactValueError("variance requires at least one value")
    if sample and len(values)<2: raise ExactValueError("sample variance requires at least two values")
    resolved=tuple(_fraction(x) for x in values)
    mean=sum(resolved,Fraction(0))/len(resolved)
    denominator=len(resolved)-1 if sample else len(resolved)
    return RationalValue(sum(((x-mean)**2 for x in resolved),Fraction(0))/denominator)

def rational_weighted_sum(values,weights,*,normalize=False):
    if len(values)!=len(weights) or not values:
        raise ExactValueError("weighted sum requires equally sized non-empty inputs")
    total=sum((_fraction(v)*_fraction(w) for v,w in zip(values,weights)),Fraction(0))
    if normalize:
        mass=sum((_fraction(w) for w in weights),Fraction(0))
        if mass==0: raise ExactValueError("cannot normalize by zero total weight")
        total/=mass
    return RationalValue(total)

__all__=[
 "ExactValueError","RationalValue","ExactPolynomial","ExactObservable","ExactObservableFrame",
 "rational_sum","rational_mean","rational_variance","rational_weighted_sum"
]
