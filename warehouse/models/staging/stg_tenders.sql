-- Staging model for raw tender rows loaded into raw.tenders by ingestion/loader.py
-- Casts types, normalises wilayas via the seed, adds metadata columns.

with

source as (
    select * from {{ source('raw', 'tenders') }}
),

renamed as (
    select
        -- Identifiers
        reference::text                                         as reference,
        detail_url::text                                        as source_url,

        -- Descriptive fields
        contracting_authority::text                             as contracting_authority,
        object::text                                            as object,
        lower(trim(tender_type))::text                         as tender_type,
        lower(trim(procedure_type))::text                      as procedure_type,

        -- Dates (already typed DATE in raw table)
        publication_date                                        as publication_date,
        deadline_date                                           as deadline_date,

        -- Geography — normalised via wilayas seed
        upper(trim(wilaya))::text                              as wilaya_raw,

        -- Metadata
        scraped_at::timestamptz                                as scraped_at,
        raw_hash::text                                         as raw_hash,
        current_timestamp                                      as _loaded_at,
        'marchespublics.gov.ma'::text                          as _source

    from source
),

normalised as (
    select
        r.*,
        coalesce(w.region_normalised, r.wilaya_raw)            as region,
        coalesce(w.wilaya_normalised, r.wilaya_raw)            as wilaya
    from renamed r
    left join {{ ref('wilayas') }} w
        on r.wilaya_raw = upper(trim(w.wilaya_raw))
),

-- Deduplicate: same reference can appear as multiple announcement types
-- (Avis d'Information, Attribution, Extrait PV). Keep the most recent row.
deduped as (
    select *,
        row_number() over (
            partition by reference
            order by scraped_at desc nulls last
        ) as _rn
    from normalised
)

select
    reference, source_url, contracting_authority, object,
    tender_type, procedure_type, publication_date, deadline_date,
    wilaya_raw, scraped_at, raw_hash, _loaded_at, _source,
    region, wilaya
from deduped
where _rn = 1
