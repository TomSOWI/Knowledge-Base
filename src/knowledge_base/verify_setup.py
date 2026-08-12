# verify_setup.py
from notion_client import Client

def verify_notion_access(api_key: str):
    client = Client(auth=api_key)
    
    #try:
    response = client.search(
        filter={"value": "page", "property": "object"},
        page_size=10
    )
    
    pages_found = len(response.get("results", []))
    
    if pages_found == 0:
        print("⚠️  Connected to API, but NO pages found.")
        print("    → Did you share your pages with the integration?")
        print("    → Go to each top-level page → '...' → Connections → Add your integration")
    else:
        print(f"✅ Success! Found {pages_found} accessible pages.")
        print("\nSample pages found:")
        for page in response["results"][:3]:
            props = page.get("properties", {})
            for prop in props.values():
                if prop.get("type") == "title":
                    title = "".join([t["plain_text"] for t in prop.get("title", [])])
                    print(f"  - {title} ({page['id']})")
                    break
                        
    # except Exception as e:
    #     print(f"❌ Connection failed: {e}")
    #     print("   → Double-check your NOTION_API_KEY in .env")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    verify_notion_access(os.getenv("NOTION_API_KEY"))