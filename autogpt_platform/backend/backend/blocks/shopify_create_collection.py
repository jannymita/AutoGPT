import shopify
import json
from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField

class CreateCollectionBlock(Block):
    api_version = "2025-01"
    class Input(BlockSchema):
        shop_name: str = SchemaField(description="The Shopify store name")
        admin_api_key: str = SchemaField(description="The API key of the Shopify store")
        collection_data: dict = SchemaField(description="The data to create the collection")

    class Output(BlockSchema):
        collection_ids: dict = SchemaField(description="A dictionary of collection IDs")

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
                            "title": "Men's Clothing"
                        }
                    },
                    "collection_KdHXk9": {
                        "type": "collection",
                        "settings": {
                            "collection": "women",
                            "title": "Women's Clothing"
                        }
                    }
                },
            },
            test_output={
                "collection_ids": {
                    "collection_rznnLq": "123456789",
                    "collection_KdHXk9": "987654321"
                },
            },
        )

    @staticmethod
    def validate_input_data(collection_data):
        """Validate the required input data for creating collections."""
        for key, collection in collection_data.items():
            if not collection.get("settings", {}).get("collection"):
                raise ValueError(f"Collection '{key}' must have a 'collection' field.")
            

    def create_smart_collection(self, collection_data):
        """Create smart collections based on tag conditions using Shopify GraphQL API."""

        print("Creating smart collections...")
        collection_ids = {}

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

            # Construct the GraphQL query for creating the Smart Collection
            query = """
            mutation CollectionCreate($input: CollectionInput!) {
                    collectionCreate(input: $input) {
                        userErrors {
                        field
                        message
                        }
                        collection {
                        id
                        title
                        descriptionHtml
                        handle
                        sortOrder
                        ruleSet {
                            appliedDisjunctively
                            rules {
                            column
                            relation
                            condition
                            }
                        }
                        }
                    }
                }
            """

            params = {
                {
                    "input": {
                        "title": collection_title,
                        "descriptionHtml": collection_title,
                        "ruleSet": {
                        "appliedDisjunctively": False, #Whether products must match any or all of the rules to be included in the collection. If true, then products must match at least one of the rules to be included in the collection. If false, then products must match all of the rules to be included in the collection.
                        "rules": {
                            "column": "TAG",
                            "relation": "EQUALS",
                            "condition": collection_title
                            }
                        }
                    }
                }

            }

            try:
                print("sending request")
                # Execute the GraphQL query
                response = shopify.GraphQL().execute(query, params)
                response = json.loads(response)

                # Check for errors in the response
                if 'data' in response and 'collectionCreate' in response['data']:
                    created_collection = response['data']['collectionCreate']['collection']
                    collection_ids[collection_key] = created_collection['id']
                else:
                    errors = response.get('errors', [])
                    if errors:
                        raise ValueError(f"Error creating collection '{collection_key}': {errors}")
                    else:
                        raise ValueError(f"Unknown error creating collection '{collection_key}'")

            except Exception as e:
                raise ValueError(f"Error executing GraphQL request for collection '{collection_key}': {str(e)}")

        return collection_ids

    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        """Run the block with the provided input data."""
        try:

            # Set up the Shopify session
            shop_url = f"https://{input_data.shop_name}.myshopify.com"
            session = shopify.Session(shop_url, self.api_version, input_data.admin_api_key)
            shopify.ShopifyResource.activate_session(session)
            # Validate the input data
            self.validate_input_data(input_data.collection_data)

            # Create the smart collections using tags and get the results

            collection_ids = self.create_smart_collection(input_data.collection_data)

            shopify.ShopifyResource.clear_session()

            # Yield the collection IDs and handles as output
            yield "collection_ids", {}

        except ValueError as ve:
            # Handle validation errors
            yield "error", f"Validation error: {ve}"

        except Exception as e:
            # Handle unexpected errors
            yield "error", f"An unexpected error occurred: {e}"
