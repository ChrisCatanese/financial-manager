"""User-specific configuration for the tax pipeline — hierarchical knowledge model.

All personal data (names, paths, folder structures, known facts) lives here
rather than being hardcoded in engine modules.  The knowledge graph is layered::

    Filers ─▶ Employers
    Properties ─▶ Mortgage · Solar · TaxAuthority
    FinancialAccounts ─▶ Institution · ExpectedForms
    Folders ─▶ Context
    KnownFacts ─▶ Manual inputs

Load order:

1. ``config/user-config.yaml`` (gitignored) — the real config
2. Falls back to environment variable ``FM_USER_CONFIG``
3. Falls back to empty defaults (pipeline runs but extracts nothing)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ── Filer layer ───────────────────────────────────────────────────────


@dataclass
class Employer:
    """An employer associated with a filer.

    Attributes:
        name: Employer legal name (used for W-2 matching).
        ein_last4: Last four digits of the employer EIN.
        name_patterns: Additional regex patterns for filename matching.
    """

    name: str = ""
    ein_last4: str = ""
    name_patterns: list[str] = field(default_factory=list)


@dataclass
class Filer:
    """Identity of a primary or secondary filer.

    Attributes:
        first_name: First name (used for filename matching).
        last_name: Last name.
        role: Either ``"primary"`` or ``"spouse"``.
        name_patterns: Additional regex patterns to match this filer in filenames.
        employers: Employers associated with this filer.
    """

    first_name: str = ""
    last_name: str = ""
    role: str = "primary"
    name_patterns: list[str] = field(default_factory=list)
    employers: list[Employer] = field(default_factory=list)


# Backward-compat alias so existing imports keep working.
FilerInfo = Filer


@dataclass
class Dependent:
    """A qualifying dependent of the filer(s).

    Attributes:
        first_name: Dependent first name.
        last_name: Dependent last name.
        date_of_birth: Date of birth (ISO or MM/DD/YYYY string).
        relationship: Relationship to primary filer (e.g. ``"child"``).
        ssn_last4: Last four digits of the dependent SSN.
        qualifies_ctc: Whether the dependent qualifies for the Child Tax Credit.
        qualifies_odc: Whether the dependent qualifies for the Other Dependent Credit.
        full_time_student: Whether the dependent is a full-time student.
    """

    first_name: str = ""
    last_name: str = ""
    date_of_birth: str = ""
    relationship: str = ""
    ssn_last4: str = ""
    qualifies_ctc: bool = False
    qualifies_odc: bool = False
    full_time_student: bool = False


# ── Property layer ────────────────────────────────────────────────────


@dataclass
class MortgageInfo:
    """Mortgage details for a property.

    Attributes:
        servicer: Mortgage servicer name (for 1098 matching).
        account_last4: Last four digits of the mortgage account.
        origination_date: Loan origination date string.
        original_balance: Original loan balance.
    """

    servicer: str = ""
    account_last4: str = ""
    origination_date: str = ""
    original_balance: float = 0.0


@dataclass
class SolarInstallation:
    """Solar panel installation details for the Residential Clean Energy Credit.

    Attributes:
        installer: Installer company name.
        installed_date: Date placed in service (MM/DD/YYYY).
        system_size_kw: System size in kilowatts.
        total_cost: Total cost including installation.
        includes_battery: Whether the installation includes battery storage.
    """

    installer: str = ""
    installed_date: str = ""
    system_size_kw: float = 0.0
    total_cost: float = 0.0
    includes_battery: bool = False


@dataclass
class PropertyTaxAuthority:
    """Tax authority information for a property.

    Attributes:
        municipality: Municipality or township name.
        county: County name.
        state: Two-letter state code.
        parcel_id: Tax parcel or lot identifier.
    """

    municipality: str = ""
    county: str = ""
    state: str = ""
    parcel_id: str = ""


@dataclass
class Property:
    """A real-estate property relevant to the return.

    Attributes:
        label: Short human-readable label (e.g. ``"Main House"``).
        address: Street address.
        city: City name.
        state: Two-letter state code.
        zip_code: Five- or nine-digit ZIP.
        property_type: ``"single_family"``, ``"condo"``, ``"townhouse"``, etc.
        role: ``"primary_residence"``, ``"sold"``, ``"purchased"``, ``"rental"``.
        purchase_date: Date of original purchase.
        purchase_price: Original purchase price (cost basis).
        sale_date: Date of sale (empty if not sold).
        sale_price: Sale price (zero if not sold).
        capital_improvements: Total capital improvements added to basis.
        section_121_eligible: Whether Sec. 121 home-sale exclusion applies.
        mortgage: Mortgage details.
        solar: Solar installation details.
        tax_authority: Tax authority info.
        title_company: Title/settlement company name.
        folder_context: Folder context hint (``"house"``, ``"condo"``).
    """

    label: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    property_type: str = ""
    role: str = "primary_residence"
    purchase_date: str = ""
    purchase_price: float = 0.0
    sale_date: str = ""
    sale_price: float = 0.0
    capital_improvements: float = 0.0
    section_121_eligible: bool = False
    mortgage: MortgageInfo = field(default_factory=MortgageInfo)
    solar: SolarInstallation = field(default_factory=SolarInstallation)
    tax_authority: PropertyTaxAuthority = field(default_factory=PropertyTaxAuthority)
    title_company: str = ""
    folder_context: str = ""


# ── Financial accounts layer ──────────────────────────────────────────


@dataclass
class FinancialAccount:
    """A financial account whose statements produce tax forms.

    Attributes:
        institution: Institution name (for filename matching).
        account_type: ``"brokerage"``, ``"bank"``, ``"retirement"``, ``"hsa"``.
        account_last4: Last four digits of the account number.
        name_patterns: Additional regex patterns for filename matching.
        owner: ``"primary"``, ``"spouse"``, or ``"joint"``.
        expected_forms: Tax forms expected from this account (e.g. ``["1099_consolidated"]``).
        export_path: Path to folder where CSV/OFX/QFX exports from this institution are saved.
    """

    institution: str = ""
    account_type: str = "brokerage"
    account_last4: str = ""
    name_patterns: list[str] = field(default_factory=list)
    owner: str = "primary"
    expected_forms: list[str] = field(default_factory=list)
    export_path: str = ""


# ── Folder layer ──────────────────────────────────────────────────────


@dataclass
class FolderDef:
    """Definition of a document source folder.

    Attributes:
        path: Filesystem path (supports ``~`` and env vars).
        label: Human-readable label for logging.
        recursive: Whether to scan subfolders.
        tax_year_filter: If set, only include files for this tax year.
        context: Folder context hint (``tax``, ``house``, ``condo``, ``general``).
    """

    path: str = ""
    label: str = ""
    recursive: bool = True
    tax_year_filter: int | None = None
    context: str = "general"


# ── Known facts layer ─────────────────────────────────────────────────


@dataclass
class KnownFacts:
    """User-provided facts that cannot be extracted from documents.

    Attributes:
        estimated_tax_payments: Total estimated tax payments made during the year.
        charitable_cash: Cash charitable contributions.
        charitable_noncash: Non-cash charitable contributions (fair market value).
        medical_expenses: Unreimbursed medical/dental expenses.
        educator_expenses: Eligible educator expenses (up to IRS limit).
        student_loan_interest: Student loan interest paid.
        ira_contributions: Traditional IRA contributions.
        hsa_contributions: HSA contributions (outside payroll).
        notes: Free-form notes or reminders for the preparer.
    """

    estimated_tax_payments: float = 0.0
    charitable_cash: float = 0.0
    charitable_noncash: float = 0.0
    medical_expenses: float = 0.0
    educator_expenses: float = 0.0
    student_loan_interest: float = 0.0
    ira_contributions: float = 0.0
    hsa_contributions: float = 0.0
    notes: list[str] = field(default_factory=list)


# ── Root configuration ────────────────────────────────────────────────


@dataclass
class UserConfig:
    """Complete user configuration for the tax pipeline.

    The dataclass stores the canonical hierarchical data.  Flat convenience
    accessors (``brokerage_names``, ``employer_names``, etc.) are provided as
    ``@property`` methods so that downstream code can use the simple API while
    the knowledge lives in one place.

    Attributes:
        tax_year: Target tax year.
        filing_status: IRS filing status string.
        primary_filer: Primary taxpayer identity.
        spouse: Spouse identity (empty if not filing jointly).
        dependents: Qualifying dependents.
        properties: Real-estate properties relevant to the return.
        accounts: Financial accounts that produce tax forms.
        folders: Document source folders to scan.
        known_facts: User-provided facts.
    """

    tax_year: int = 2025
    filing_status: str = "married_filing_jointly"
    primary_filer: Filer = field(default_factory=Filer)
    spouse: Filer = field(default_factory=lambda: Filer(role="spouse"))
    dependents: list[Dependent] = field(default_factory=list)
    properties: list[Property] = field(default_factory=list)
    accounts: list[FinancialAccount] = field(default_factory=list)
    folders: list[FolderDef] = field(default_factory=list)
    known_facts: KnownFacts = field(default_factory=KnownFacts)

    # ── Filer helpers ─────────────────────────────────────────────

    @property
    def filers(self) -> list[Filer]:
        """All filers (primary + spouse if present)."""
        result: list[Filer] = [self.primary_filer]
        if self.spouse.first_name:
            result.append(self.spouse)
        return result

    @property
    def all_employers(self) -> list[Employer]:
        """Flat list of employers from every filer."""
        employers: list[Employer] = []
        for filer in self.filers:
            employers.extend(filer.employers)
        return employers

    @property
    def employer_names(self) -> list[str]:
        """Employer names across all filers."""
        return [e.name for e in self.all_employers if e.name]

    # ── Account helpers ───────────────────────────────────────────

    @property
    def brokerage_accounts(self) -> list[FinancialAccount]:
        """Brokerage accounts."""
        return [a for a in self.accounts if a.account_type == "brokerage"]

    @property
    def bank_accounts(self) -> list[FinancialAccount]:
        """Bank / checking / savings accounts."""
        return [a for a in self.accounts if a.account_type == "bank"]

    @property
    def retirement_accounts(self) -> list[FinancialAccount]:
        """Retirement (401k, IRA, etc.) accounts."""
        return [a for a in self.accounts if a.account_type == "retirement"]

    @property
    def hsa_accounts(self) -> list[FinancialAccount]:
        """HSA accounts."""
        return [a for a in self.accounts if a.account_type == "hsa"]

    @property
    def brokerage_names(self) -> list[str]:
        """Institution names of brokerage accounts."""
        return [a.institution for a in self.brokerage_accounts if a.institution]

    @property
    def bank_names(self) -> list[str]:
        """Institution names of bank accounts."""
        return [a.institution for a in self.bank_accounts if a.institution]

    # ── Property helpers ──────────────────────────────────────────

    @property
    def sold_properties(self) -> list[Property]:
        """Properties with role ``"sold"``."""
        return [p for p in self.properties if p.role == "sold"]

    @property
    def purchased_properties(self) -> list[Property]:
        """Properties with role ``"purchased"``."""
        return [p for p in self.properties if p.role == "purchased"]

    @property
    def primary_residence(self) -> Property | None:
        """First property with role ``"primary_residence"``, or *None*."""
        for p in self.properties:
            if p.role == "primary_residence":
                return p
        return None

    @property
    def mortgage_servicers(self) -> list[str]:
        """Mortgage servicer names across all properties."""
        return [
            p.mortgage.servicer
            for p in self.properties
            if p.mortgage and p.mortgage.servicer
        ]

    @property
    def title_companies(self) -> list[str]:
        """Title / settlement company names across all properties."""
        return [p.title_company for p in self.properties if p.title_company]

    @property
    def municipalities(self) -> list[str]:
        """Municipality names from property tax authorities."""
        return [
            p.tax_authority.municipality
            for p in self.properties
            if p.tax_authority and p.tax_authority.municipality
        ]

    @property
    def solar_installations(self) -> list[SolarInstallation]:
        """Solar installations that have meaningful data."""
        return [
            p.solar
            for p in self.properties
            if p.solar and (p.solar.installed_date or p.solar.total_cost)
        ]

    @property
    def children_count(self) -> int:
        """Number of dependents qualifying for the Child Tax Credit."""
        return sum(1 for d in self.dependents if d.qualifies_ctc)


# ── Path helpers ──────────────────────────────────────────────────────


def _resolve_path(raw: str) -> Path:
    """Expand ``~``, env vars, and resolve a path string.

    Args:
        raw: Raw path string from config.

    Returns:
        Resolved absolute Path.
    """
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


# ── YAML loading ──────────────────────────────────────────────────────


def load_user_config(config_path: str | Path | None = None) -> UserConfig:
    """Load user configuration from a YAML file.

    Args:
        config_path: Explicit path to config file.  If *None*, searches:
            1. ``config/user-config.yaml`` in the project root
            2. ``FM_USER_CONFIG`` environment variable

    Returns:
        Populated UserConfig, or empty defaults if no config found.
    """
    if config_path is None:
        default_path = _PROJECT_ROOT / "config" / "user-config.yaml"
        env_path = os.environ.get("FM_USER_CONFIG")
        if default_path.exists():
            config_path = default_path
        elif env_path and Path(env_path).exists():
            config_path = Path(env_path)
        else:
            logger.warning(
                "No user config found at %s or FM_USER_CONFIG — using empty defaults",
                default_path,
            )
            return UserConfig()

    path = Path(config_path)
    if not path.exists():
        logger.warning("Config file not found: %s — using empty defaults", path)
        return UserConfig()

    try:
        import yaml
    except ImportError:
        logger.error(
            "PyYAML not installed — cannot load user config. Run: pip install pyyaml"
        )
        return UserConfig()

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        logger.warning("Invalid config format in %s — using empty defaults", path)
        return UserConfig()

    return _parse_config(raw)


# ── Internal parsing ──────────────────────────────────────────────────


def _parse_employer(raw: dict) -> Employer:  # type: ignore[type-arg]
    """Parse a raw YAML dict into an Employer.

    Args:
        raw: Single employer mapping from YAML.

    Returns:
        Populated Employer.
    """
    return Employer(
        name=str(raw.get("name", "")),
        ein_last4=str(raw.get("ein_last4", "")),
        name_patterns=[str(p) for p in raw.get("name_patterns", [])],
    )


def _parse_filer(raw: dict, role: str = "primary") -> Filer:  # type: ignore[type-arg]
    """Parse a raw YAML dict into a Filer.

    Args:
        raw: Filer mapping from YAML.
        role: ``"primary"`` or ``"spouse"``.

    Returns:
        Populated Filer.
    """
    employers = [_parse_employer(e) for e in raw.get("employers", [])]
    return Filer(
        first_name=str(raw.get("first_name", "")),
        last_name=str(raw.get("last_name", "")),
        role=role,
        name_patterns=[str(p) for p in raw.get("name_patterns", [])],
        employers=employers,
    )


def _parse_dependent(raw: dict) -> Dependent:  # type: ignore[type-arg]
    """Parse a raw YAML dict into a Dependent.

    Args:
        raw: Dependent mapping from YAML.

    Returns:
        Populated Dependent.
    """
    return Dependent(
        first_name=str(raw.get("first_name", "")),
        last_name=str(raw.get("last_name", "")),
        date_of_birth=str(raw.get("date_of_birth", "")),
        relationship=str(raw.get("relationship", "")),
        ssn_last4=str(raw.get("ssn_last4", "")),
        qualifies_ctc=bool(raw.get("qualifies_ctc", False)),
        qualifies_odc=bool(raw.get("qualifies_odc", False)),
        full_time_student=bool(raw.get("full_time_student", False)),
    )


def _parse_mortgage(raw: dict) -> MortgageInfo:  # type: ignore[type-arg]
    """Parse a raw YAML dict into a MortgageInfo.

    Args:
        raw: Mortgage mapping from YAML.

    Returns:
        Populated MortgageInfo.
    """
    return MortgageInfo(
        servicer=str(raw.get("servicer", "")),
        account_last4=str(raw.get("account_last4", "")),
        origination_date=str(raw.get("origination_date", "")),
        original_balance=float(raw.get("original_balance", 0.0)),
    )


def _parse_solar(raw: dict) -> SolarInstallation:  # type: ignore[type-arg]
    """Parse a raw YAML dict into a SolarInstallation.

    Args:
        raw: Solar mapping from YAML.

    Returns:
        Populated SolarInstallation.
    """
    return SolarInstallation(
        installer=str(raw.get("installer", "")),
        installed_date=str(raw.get("installed_date", "")),
        system_size_kw=float(raw.get("system_size_kw", 0.0)),
        total_cost=float(raw.get("total_cost", 0.0)),
        includes_battery=bool(raw.get("includes_battery", False)),
    )


def _parse_tax_authority(raw: dict) -> PropertyTaxAuthority:  # type: ignore[type-arg]
    """Parse a raw YAML dict into a PropertyTaxAuthority.

    Args:
        raw: Tax authority mapping from YAML.

    Returns:
        Populated PropertyTaxAuthority.
    """
    return PropertyTaxAuthority(
        municipality=str(raw.get("municipality", "")),
        county=str(raw.get("county", "")),
        state=str(raw.get("state", "")),
        parcel_id=str(raw.get("parcel_id", "")),
    )


def _parse_property(raw: dict) -> Property:  # type: ignore[type-arg]
    """Parse a raw YAML dict into a Property.

    Args:
        raw: Property mapping from YAML.

    Returns:
        Populated Property.
    """
    mortgage_raw = raw.get("mortgage")
    mortgage = _parse_mortgage(mortgage_raw) if mortgage_raw else MortgageInfo()

    solar_raw = raw.get("solar")
    solar = _parse_solar(solar_raw) if solar_raw else SolarInstallation()

    ta_raw = raw.get("tax_authority")
    tax_authority = _parse_tax_authority(ta_raw) if ta_raw else PropertyTaxAuthority()

    return Property(
        label=str(raw.get("label", "")),
        address=str(raw.get("address", "")),
        city=str(raw.get("city", "")),
        state=str(raw.get("state", "")),
        zip_code=str(raw.get("zip_code", "")),
        property_type=str(raw.get("property_type", "")),
        role=str(raw.get("role", "primary_residence")),
        purchase_date=str(raw.get("purchase_date", "")),
        purchase_price=float(raw.get("purchase_price", 0.0)),
        sale_date=str(raw.get("sale_date", "")),
        sale_price=float(raw.get("sale_price", 0.0)),
        capital_improvements=float(raw.get("capital_improvements", 0.0)),
        section_121_eligible=bool(raw.get("section_121_eligible", False)),
        mortgage=mortgage,
        solar=solar,
        tax_authority=tax_authority,
        title_company=str(raw.get("title_company", "")),
        folder_context=str(raw.get("folder_context", "")),
    )


def _parse_account(raw: dict) -> FinancialAccount:  # type: ignore[type-arg]
    """Parse a raw YAML dict into a FinancialAccount.

    Args:
        raw: Account mapping from YAML.

    Returns:
        Populated FinancialAccount.
    """
    return FinancialAccount(
        institution=str(raw.get("institution", "")),
        account_type=str(raw.get("account_type", "brokerage")),
        account_last4=str(raw.get("account_last4", "")),
        name_patterns=[str(p) for p in raw.get("name_patterns", [])],
        owner=str(raw.get("owner", "primary")),
        expected_forms=[str(f) for f in raw.get("expected_forms", [])],
        export_path=str(raw.get("export_path", "")),
    )


def _parse_folder(raw: dict) -> FolderDef:  # type: ignore[type-arg]
    """Parse a raw YAML dict into a FolderDef.

    Args:
        raw: Folder mapping from YAML.

    Returns:
        Populated FolderDef.
    """
    return FolderDef(
        path=str(raw.get("path", "")),
        label=str(raw.get("label", "")),
        recursive=bool(raw.get("recursive", True)),
        tax_year_filter=raw.get("tax_year_filter"),
        context=str(raw.get("context", "general")),
    )


def _parse_known_facts(raw: dict) -> KnownFacts:  # type: ignore[type-arg]
    """Parse a raw YAML dict into KnownFacts.

    Args:
        raw: Known-facts mapping from YAML.

    Returns:
        Populated KnownFacts.
    """
    return KnownFacts(
        estimated_tax_payments=float(raw.get("estimated_tax_payments", 0.0)),
        charitable_cash=float(raw.get("charitable_cash", 0.0)),
        charitable_noncash=float(raw.get("charitable_noncash", 0.0)),
        medical_expenses=float(raw.get("medical_expenses", 0.0)),
        educator_expenses=float(raw.get("educator_expenses", 0.0)),
        student_loan_interest=float(raw.get("student_loan_interest", 0.0)),
        ira_contributions=float(raw.get("ira_contributions", 0.0)),
        hsa_contributions=float(raw.get("hsa_contributions", 0.0)),
        notes=[str(n) for n in raw.get("notes", [])],
    )


def _parse_config(raw: dict) -> UserConfig:  # type: ignore[type-arg]
    """Parse a raw YAML dict into a UserConfig.

    Handles both the **new hierarchical** format (``properties``, ``accounts``,
    ``dependents``, ``Filer.employers``) and the **legacy flat** format
    (``brokerage_names``, ``employer_names``, ``mortgage_servicer``, etc.) so
    that existing ``config/user-config.yaml`` files continue to work during the
    migration period.

    Args:
        raw: Parsed YAML data.

    Returns:
        Populated UserConfig.
    """
    cfg = UserConfig()
    cfg.tax_year = int(raw.get("tax_year", 2025))
    cfg.filing_status = str(raw.get("filing_status", "married_filing_jointly"))

    # ── Filers ────────────────────────────────────────────────────
    pf = raw.get("primary_filer", {})
    if pf:
        cfg.primary_filer = _parse_filer(pf, role="primary")

    sp = raw.get("spouse", {})
    if sp:
        cfg.spouse = _parse_filer(sp, role="spouse")

    # ── Dependents ────────────────────────────────────────────────
    for dep_raw in raw.get("dependents", []):
        cfg.dependents.append(_parse_dependent(dep_raw))

    # ── Properties ────────────────────────────────────────────────
    for prop_raw in raw.get("properties", []):
        cfg.properties.append(_parse_property(prop_raw))

    # ── Financial accounts ────────────────────────────────────────
    for acct_raw in raw.get("accounts", []):
        cfg.accounts.append(_parse_account(acct_raw))

    # ── Folders ───────────────────────────────────────────────────
    for folder_raw in raw.get("folders", []):
        cfg.folders.append(_parse_folder(folder_raw))

    # ── Known facts ───────────────────────────────────────────────
    kf = raw.get("known_facts", {})
    if kf:
        cfg.known_facts = _parse_known_facts(kf)

    # ── Legacy flat-field migration ───────────────────────────────
    # If the YAML still uses the old flat keys, hoist them into the
    # hierarchical model so downstream code sees a consistent shape.
    _migrate_legacy_fields(raw, cfg)

    return cfg


def _migrate_legacy_fields(raw: dict, cfg: UserConfig) -> None:  # type: ignore[type-arg]
    """Migrate legacy flat YAML keys into the hierarchical model.

    This ensures that existing ``config/user-config.yaml`` files with keys like
    ``brokerage_names``, ``employer_names``, ``mortgage_servicer``, etc. still
    work after the schema upgrade.

    Args:
        raw: Original YAML dict.
        cfg: Partially-populated UserConfig to mutate in place.
    """
    # Legacy employer_names → Employer objects on primary_filer
    legacy_employers = [str(e) for e in raw.get("employer_names", [])]
    if legacy_employers and not cfg.primary_filer.employers:
        for name in legacy_employers:
            cfg.primary_filer.employers.append(Employer(name=name))

    # Legacy brokerage_names → FinancialAccount(account_type="brokerage")
    legacy_brokerages = [str(b) for b in raw.get("brokerage_names", [])]
    if legacy_brokerages and not cfg.brokerage_accounts:
        for name in legacy_brokerages:
            cfg.accounts.append(
                FinancialAccount(institution=name, account_type="brokerage")
            )

    # Legacy bank_names → FinancialAccount(account_type="bank")
    legacy_banks = [str(b) for b in raw.get("bank_names", [])]
    if legacy_banks and not cfg.bank_accounts:
        for name in legacy_banks:
            cfg.accounts.append(
                FinancialAccount(institution=name, account_type="bank")
            )

    # Legacy mortgage_servicer → Property.mortgage
    legacy_mortgage = str(raw.get("mortgage_servicer", ""))
    if legacy_mortgage and not cfg.mortgage_servicers:
        if cfg.properties:
            cfg.properties[0].mortgage.servicer = legacy_mortgage
        else:
            cfg.properties.append(
                Property(
                    label="(migrated)",
                    role="primary_residence",
                    mortgage=MortgageInfo(servicer=legacy_mortgage),
                )
            )

    # Legacy title_company → Property.title_company
    legacy_title = str(raw.get("title_company", ""))
    if legacy_title and not cfg.title_companies:
        if cfg.properties:
            cfg.properties[0].title_company = legacy_title
        else:
            cfg.properties.append(
                Property(label="(migrated)", title_company=legacy_title)
            )

    # Legacy municipality → Property.tax_authority.municipality
    legacy_muni = str(raw.get("municipality", ""))
    if legacy_muni and not cfg.municipalities:
        if cfg.properties:
            cfg.properties[0].tax_authority.municipality = legacy_muni
        else:
            cfg.properties.append(
                Property(
                    label="(migrated)",
                    tax_authority=PropertyTaxAuthority(municipality=legacy_muni),
                )
            )

    # Legacy known_facts fields that moved to Property
    kf_raw = raw.get("known_facts", {})
    if kf_raw:
        legacy_solar_date = str(kf_raw.get("solar_installed_date", ""))
        if legacy_solar_date and not cfg.solar_installations:
            if cfg.properties:
                cfg.properties[0].solar.installed_date = legacy_solar_date
            else:
                cfg.properties.append(
                    Property(
                        label="(migrated)",
                        solar=SolarInstallation(installed_date=legacy_solar_date),
                    )
                )

        legacy_purchase_price = float(kf_raw.get("original_purchase_price", 0))
        if legacy_purchase_price and cfg.properties and not any(
            p.purchase_price for p in cfg.properties
        ):
            cfg.properties[0].purchase_price = legacy_purchase_price

        legacy_cap_improvements = float(kf_raw.get("capital_improvements", 0))
        if legacy_cap_improvements and cfg.properties and not any(
            p.capital_improvements for p in cfg.properties
        ):
            cfg.properties[0].capital_improvements = legacy_cap_improvements

        legacy_121 = bool(kf_raw.get("section_121_eligible", False))
        if legacy_121 and cfg.properties:
            cfg.properties[0].section_121_eligible = legacy_121

        # Legacy children_count / children_ages → Dependent stubs
        legacy_count = int(kf_raw.get("children_count", 0))
        legacy_ages: list[int] = [int(a) for a in kf_raw.get("children_ages", [])]
        if legacy_count and not cfg.dependents:
            for i in range(legacy_count):
                age = legacy_ages[i] if i < len(legacy_ages) else 0
                cfg.dependents.append(
                    Dependent(
                        first_name=f"Child {i + 1}",
                        relationship="child",
                        qualifies_ctc=True,
                        date_of_birth=str(age),  # placeholder
                    )
                )


# ── Dynamic rule builders ─────────────────────────────────────────────


def build_spouse_w2_patterns(config: UserConfig) -> list[re.Pattern[str]]:
    """Build regex patterns for matching spouse W-2 filenames.

    Args:
        config: The user configuration.

    Returns:
        List of compiled regex patterns.  Empty if no spouse configured.
    """
    patterns: list[re.Pattern[str]] = []
    if not config.spouse.first_name:
        return patterns

    name = re.escape(config.spouse.first_name)
    patterns.append(re.compile(rf"{name}.*w[\-\s]?2", re.IGNORECASE))
    patterns.append(re.compile(rf"w[\-\s]?2.*{name}", re.IGNORECASE))

    for extra in config.spouse.name_patterns:
        patterns.append(re.compile(extra, re.IGNORECASE))

    return patterns


def build_brokerage_patterns(config: UserConfig) -> list[re.Pattern[str]]:
    """Build regex patterns for matching brokerage consolidated 1099 filenames.

    Iterates ``config.brokerage_accounts`` (not a flat name list) so that the
    hierarchical account model is the single source of truth.

    Args:
        config: The user configuration.

    Returns:
        List of compiled regex patterns.  Empty if no brokerages configured.
    """
    patterns: list[re.Pattern[str]] = []
    for acct in config.brokerage_accounts:
        if not acct.institution:
            continue
        escaped = re.escape(acct.institution)
        patterns.append(
            re.compile(rf"{escaped}.*1099|1099.*{escaped}", re.IGNORECASE)
        )
        for extra in acct.name_patterns:
            patterns.append(re.compile(extra, re.IGNORECASE))
    return patterns


def build_classification_rules(
    config: UserConfig,
) -> list[tuple[re.Pattern[str], str]]:
    """Build a complete ordered set of filename → document-type classification rules.

    The rules are layered so that the most specific match wins:

    1. **Spouse name** → ``w2_spouse``
    2. **Employer names** → ``w2`` or ``w2_spouse`` depending on filer role
    3. **Financial accounts** → type-appropriate 1099 variant
    4. **Property details** → mortgage / title / municipality forms
    5. **Solar installer** → ``solar_agreement``

    Args:
        config: The user configuration.

    Returns:
        Ordered list of ``(compiled_pattern, TaxDocumentType_value)`` tuples.
    """
    rules: list[tuple[re.Pattern[str], str]] = []

    # ── Layer 1: Spouse name → w2_spouse ──────────────────────────
    if config.spouse.first_name:
        name = re.escape(config.spouse.first_name)
        rules.append(
            (re.compile(rf"{name}.*w[\-\s]?2", re.IGNORECASE), "w2_spouse")
        )
        rules.append(
            (re.compile(rf"w[\-\s]?2.*{name}", re.IGNORECASE), "w2_spouse")
        )
        for extra in config.spouse.name_patterns:
            rules.append((re.compile(extra, re.IGNORECASE), "w2_spouse"))

    # ── Layer 2: Employer names → w2 / w2_spouse ──────────────────
    for filer in config.filers:
        doc_type = "w2" if filer.role == "primary" else "w2_spouse"
        for emp in filer.employers:
            if emp.name:
                escaped = re.escape(emp.name)
                rules.append(
                    (re.compile(rf"{escaped}.*w[\-\s]?2", re.IGNORECASE), doc_type)
                )
                rules.append(
                    (re.compile(rf"w[\-\s]?2.*{escaped}", re.IGNORECASE), doc_type)
                )
            for pat in emp.name_patterns:
                rules.append((re.compile(pat, re.IGNORECASE), doc_type))

    # ── Layer 3: Financial accounts → form type ───────────────────
    account_type_map: dict[str, str] = {
        "brokerage": "1099_consolidated",
        "bank": "1099_int",
        "retirement": "1099_r",
        "hsa": "1099_sa",
    }
    for acct in config.accounts:
        target = account_type_map.get(acct.account_type)
        if not target or not acct.institution:
            continue
        escaped = re.escape(acct.institution)
        rules.append(
            (re.compile(rf"{escaped}", re.IGNORECASE), target)
        )
        for pat in acct.name_patterns:
            rules.append((re.compile(pat, re.IGNORECASE), target))

    # ── Layer 4: Property details ─────────────────────────────────
    for prop in config.properties:
        # Mortgage servicer → 1098
        if prop.mortgage and prop.mortgage.servicer:
            escaped = re.escape(prop.mortgage.servicer)
            rules.append(
                (re.compile(rf"{escaped}", re.IGNORECASE), "1098")
            )

        # Title company → settlement_statement
        if prop.title_company:
            escaped = re.escape(prop.title_company)
            rules.append(
                (re.compile(rf"{escaped}", re.IGNORECASE), "settlement_statement")
            )

        # Municipality → property_tax_bill
        if prop.tax_authority and prop.tax_authority.municipality:
            escaped = re.escape(prop.tax_authority.municipality)
            rules.append(
                (re.compile(rf"{escaped}", re.IGNORECASE), "property_tax_bill")
            )

    # ── Layer 5: Solar installer → solar_agreement ────────────────
    for prop in config.properties:
        if prop.solar and prop.solar.installer:
            escaped = re.escape(prop.solar.installer)
            rules.append(
                (re.compile(rf"{escaped}", re.IGNORECASE), "solar_agreement")
            )

    return rules
