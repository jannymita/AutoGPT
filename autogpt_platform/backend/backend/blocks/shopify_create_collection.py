import requests
from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField

class CreateCollectionBlock(Block):
    class Input(BlockSchema):
        shop_name: str = SchemaField(description="The Shopify store name")
        admin_api_key: str = SchemaField(description="The API key of the Shopify store")
        collection_data: dict = SchemaField(description="The data to create the collection")

    class Output(BlockSchema):
        collection_ids: dict = SchemaField(description="A dictionary of collection IDs")
        collection_handles: dict = SchemaField(description="A dictionary of collection handles")

    def __init__(self):
        super().__init__(
            id="f1d8e3b8-99d0-4420-b48e-5b8e3f7beeb6",
            description="This block creates Shopify Smart Collections using tags.",
            categories={BlockCategory.SHOPIFY},
            input_schema=CreateCollectionBlock.Input,
            output_schema=CreateCollectionBlock.Output,
            test_input={
                "shop_name": "your-shop-name.myshopify.com",
                "admin_api_key": "your-admin-api-key",
                "collection_data": {
                    "collection_rznnLq": {
                        "type": "collection",
                        "settings": {
                            "collection": "men",
                            "title": "Men's Clothing",
                            "tag_condition": "sale",  # Tag condition
                            "description": "anb"   # Collection description
                        }
                    },
                    "collection_KdHXk9": {
                        "type": "collection",
                        "settings": {
                            "collection": "women",
                            "title": "Women's Clothing",
                            "tag_condition": "new-arrivals",  # Tag condition
                            "description": "anb"   # Collection description
                        }
                    }
                },
            },
            test_output={
                "collection_ids": {
                    "collection_rznnLq": "123456789",
                    "collection_KdHXk9": "987654321"
                },
                "collection_handles": {
                    "collection_rznnLq": "mens-clothing",
                    "collection_KdHXk9": "womens-clothing"
                },
            },
        )

    @staticmethod
    def validate_input_data(collection_data):
        """Validate the required input data for creating collections."""
        for key, collection in collection_data.items():
            if not collection.get("settings", {}).get("collection"):
                raise ValueError(f"Collection '{key}' must have a 'collection' field.")
            
    def create_smart_collection(self, shop_name, admin_api_key, collection_data):
        """Create smart collections based on tag conditions using Shopify API."""
        url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/smart_collections.json"
        headers = {"Content-Type": "application/json", "X-Shopify-Access-Token": admin_api_key}

        collection_ids = {}
        collection_handles = {}

        new_collections = [
        {"key": "collection_HotDeals", "collection": "hot-deals", "title": "Hot Deals"},
        {"key": "collection_Trending", "collection": "trending", "title": "Trending"},
        {"key": "collection_NewComing", "collection": "new-coming", "title": "New Coming"},
        {"key": "collection_Featured", "collection": "featured", "title": "Featured"},
        {"key": "collection_Discover", "collection": "discover", "title": "Discover"}
]

        for new_collection in new_collections:
            collection_data[new_collection["key"]] = {
                "type": "collection",
                "settings": {
                    "collection": new_collection["collection"],
                    "title": new_collection["title"]
                }
            }

        for collection_key, collection in collection_data.items():
            settings = collection.get("settings", {})
            collection_title = settings.get("title", "") or settings.get("collection", "")
            print("-------------------------", collection_title)

            # Construct the payload for creating the Smart Collection
            payload = {
                "smart_collection": {
                    "title": collection_title,
                    "body_html": " ", # Description of the collection
                    "published": True,
                    "published_scope": "global",
                    "rules": [
                        {
                            "column": "tag",  # Column to filter by (tags)
                            "relation": "equals",  # Relation to apply (equals)
                            "condition": collection_title  # Tag condition for the smart collection
                        },
                        {
                            "column": "tag",  # Column to filter by (tags)
                            "relation": "equals",  # Relation to apply (equals)
                            "condition": collection_title.lower()  # Tag condition for the smart collection
                        }
                    ],
                    "disjunctive": True  # Set to False if all conditions must be met (AND logic)
                }
            }

            try:
                # Send a POST request to Shopify's API to create the smart collection
                response = requests.post(url, json=payload, headers=headers)

                # Check if the request was successful
                if response.status_code == 201:
                    created_collection = response.json()["smart_collection"]
                    collection_ids[collection_key] = created_collection["id"]
                    collection_handles[collection_key] = created_collection["handle"]
                else:
                    raise ValueError(f"Error creating collection '{collection_key}': {response.json()}")

            except requests.exceptions.RequestException as e:
                raise ValueError(f"Request error while creating collection '{collection_key}': {str(e)}")

        return collection_ids, collection_handles

    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        """Run the block with the provided input data."""
        try:
            # Validate the input data
            self.validate_input_data(input_data.collection_data)

            # Create the smart collections using tags and get the results
            collection_ids, collection_handles = self.create_smart_collection(
                input_data.shop_name,
                input_data.admin_api_key,
                input_data.collection_data,
            )

            # Yield the collection IDs and handles as output
            yield "collection_ids", collection_ids
            yield "collection_handles", collection_handles

        except ValueError as ve:
            # Handle validation errors
            yield "error", f"Validation error: {ve}"

        except Exception as e:
            # Handle unexpected errors
            yield "error", f"An unexpected error occurred: {e}"
