import shopify
import json
from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField

class CreateCollectionBlock(Block):
    api_version = "2025-01"
    class Input(BlockSchema):
        shop_name: str = SchemaField(description="The Shopify store name")
        admin_api_key: str = SchemaField(description="The API key of the Shopify store")
        collection_data: dict = SchemaField(description="The data to create the collection", default={})

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
                    "men": {
                        "Men's Clothing"
                    }
                },
            },
            test_output={
                "collection_ids": {
                    "men": "123456789",
                },
            },
        )

    DEFAULT_COLLECTIONS = ["all", "latest", "trending"]
    def create_smart_collection(self, collection_data):
        collection_ids = {}

        for collection_name in self.DEFAULT_COLLECTIONS:
            if collection_name not in collection_data:
                collection_data[collection_name] = {
                    "title": collection_name.capitalize()
                }

        for collection_name, collection in collection_data.items():
            collection_title = collection.get("title")

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
                    "input": {
                        "title": collection_title,
                        "descriptionHtml": collection_title,
                        "ruleSet": {
                        "appliedDisjunctively": False, #Whether products must match any or all of the rules to be included in the collection. If true, then products must match at least one of the rules to be included in the collection. If false, then products must match all of the rules to be included in the collection.
                        "rules": {
                            "column": "TAG",
                            "relation": "EQUALS",
                            "condition": collection_name.lower()
                            }
                        }
                    }
                }

            try:
                # Execute the GraphQL query
                response = shopify.GraphQL().execute(query, params)
                response = json.loads(response)

                # Check for errors in the response
                if 'data' in response and 'collectionCreate' in response['data']:
                    created_collection = response['data']['collectionCreate']['collection']
                    collection_ids[collection_name] = created_collection['id']
                else:
                    errors = response.get('userErrors', [])
                    if errors:
                        raise ValueError(f"Error creating collection '{collection_name}': {errors}")
                    else:
                        raise ValueError(f"Unknown error creating collection '{collection_name}'")

            except Exception as e:
                raise ValueError(f"Error executing GraphQL request for collection '{collection_name}': {str(e)}")

        return collection_ids

    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        """Run the block with the provided input data."""
        try:
            # Set up the Shopify session
            shop_url = f"https://{input_data.shop_name}.myshopify.com"
            session = shopify.Session(shop_url, self.api_version, input_data.admin_api_key)
            shopify.ShopifyResource.activate_session(session)

            collection_ids = self.create_smart_collection(input_data.collection_data)

            publications = self.get_publications()

            for collection_id in collection_ids.values():
                for publication in publications:
                    try:
                        # Extract publication ID
                        publication_id = publication.get("id")
                        if not publication_id:
                            print(f"Skipping publication with missing ID: {publication}")
                            continue

                        # Publish the collection to the publication
                        self.publish_collection_to_publication(collection_id, publication_id)
                        print(f"Successfully published collection {collection_id} to publication {publication_id}")

                    except Exception as e:
                        # Handle any errors during the publishing process
                        print(f"Error publishing collection {collection_id} to publication {publication_id}: {str(e)}")

            # Yield the collection IDs and handles as output
            yield "collection_ids", collection_ids

        except ValueError as ve:
            # Handle validation errors
            yield "error", f"Validation error: {ve}"

        except Exception as e:
            # Handle unexpected errors
            yield "error", f"An unexpected error occurred: {e}"
        finally:
            shopify.ShopifyResource.clear_session()

    @staticmethod
    def get_publications() -> list:
        """
        Retrieve the list of publications from Shopify.

        :return: A list of publication IDs.
        """
        query = """
        query {
            publications(first: 10) {
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
        """

        publications = []

        try:
            # Execute the GraphQL query
            response = shopify.GraphQL().execute(query)

            # Ensure the response is parsed into a dictionary
            if isinstance(response, str):
                response = json.loads(response)

            # Check if the response contains the publications data
            if 'data' in response and 'publications' in response['data']:
                edges = response['data']['publications']['edges']
                for edge in edges:
                    node = edge.get('node', {})
                    pub_id = node.get('id')
                    pub_name = node.get('name')
                    if pub_id and pub_name:
                        print(f"Publication Name: {pub_name}, ID: {pub_id}")
                        publications.append({"id": pub_id, "name": pub_name})
            else:
                print("No publications found in the response.")

        except Exception as e:
            print(f"Error retrieving publications: {e}")

        return publications

    @staticmethod
    def publish_collection_to_publication(collection_id, publication_id):
        # GraphQL mutation to publish the collection to a specific publication
        query = """
        mutation PublishablePublish($collectionId: ID!, $publicationId: ID!) {
            publishablePublish(id: $collectionId, input: {publicationId: $publicationId}) {
                publishable {
                    publishedOnPublication(publicationId: $publicationId)
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        variables = {
            "collectionId": collection_id,
            "publicationId": publication_id
        }

        try:
            # Execute the GraphQL mutation
            response = shopify.GraphQL().execute(query, variables)
            response_data = json.loads(response)

            # Check for errors in the response
            if "data" in response_data and "publishablePublish" in response_data["data"]:
                user_errors = response_data["data"]["publishablePublish"]["userErrors"]
                if user_errors:
                    # Handle user errors
                    error_messages = [f"{error['field']}: {error['message']}" for error in user_errors]
                    raise ValueError(f"Errors occurred while publishing the collection: {', '.join(error_messages)}")
                else:
                    print(f"Collection {collection_id} was successfully published to {publication_id}.")
                    return response_data["data"]["publishablePublish"]
            else:
                raise ValueError("Unknown error occurred while publishing the collection.")
        except Exception as e:
            raise ValueError(f"An error occurred while publishing the collection: {e}")