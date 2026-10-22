with source as (

    select * from {{ source('raw', 'consolidated_transactions') }}

),

renamed as (

    select
        cast("Transaction ID" as integer) as transaction_id,
        cast("Transaction Date" as date) as transaction_date,
        cast(quantity as integer) as quantity,
        cast(unit_price as double) as unit_price,
        cast(unit_cost as double) as unit_cost,
        cast(standard_unit_cost as double) as standard_unit_cost,
        cast(landed_unit_cost as double) as landed_unit_cost,
        cast(pack_size as integer) as pack_size,
        cast("Product index" as integer) as product_id,
        cast("Product Name" as varchar) as product_name_on_transaction,
        cast(product_name_catalog as varchar) as product_name_catalog,
        cast(product_category as varchar) as product_category,
        cast(product_effective_from as date) as product_effective_from,
        cast(product_effective_to as date) as product_effective_to,
        cast("Store ID" as integer) as store_id,
        cast(store_name as varchar) as store_name,
        cast(state_code as varchar) as state_code,
        cast(state as varchar) as state,
        cast(region_name as varchar) as region_name,
        cast(store_type as varchar) as store_type,
        cast(store_sqft as double) as store_sqft,
        cast(direct_store_operating_costs as double) as direct_store_operating_costs,
        cast(source_system as varchar) as source_system,
        cast(ingested_at as timestamp) as ingested_at
    from source

),

fingerprinted as (

    select
        *,
        md5(to_json(struct_pack(
            transaction_id := transaction_id,
            transaction_date := transaction_date,
            quantity := quantity,
            unit_price := unit_price,
            unit_cost := unit_cost,
            standard_unit_cost := standard_unit_cost,
            landed_unit_cost := landed_unit_cost,
            pack_size := pack_size,
            product_id := product_id,
            product_name_on_transaction := product_name_on_transaction,
            product_name_catalog := product_name_catalog,
            product_category := product_category,
            product_effective_from := product_effective_from,
            product_effective_to := product_effective_to,
            store_id := store_id,
            store_name := store_name,
            state_code := state_code,
            state := state,
            region_name := region_name,
            store_type := store_type,
            store_sqft := store_sqft,
            direct_store_operating_costs := direct_store_operating_costs,
            source_system := source_system,
            ingested_at := ingested_at
        ))) as source_row_fingerprint
    from renamed

)

select * from fingerprinted
