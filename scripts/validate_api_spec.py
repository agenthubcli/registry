#!/usr/bin/env python3
"""
API specification validation and testing script for AgentHub Registry.
"""

import argparse
import json
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List
import requests
import time


def load_api_spec(spec_path: str) -> Dict[str, Any]:
    """Load and parse the OpenAPI specification."""
    try:
        with open(spec_path, 'r') as f:
            if spec_path.endswith('.yaml') or spec_path.endswith('.yml'):
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load API spec: {e}")
        sys.exit(1)


def validate_openapi_spec(spec: Dict[str, Any]) -> bool:
    """Validate OpenAPI specification structure."""
    print("🔍 Validating OpenAPI specification...")
    
    required_fields = ['openapi', 'info', 'paths']
    missing_fields = [field for field in required_fields if field not in spec]
    
    if missing_fields:
        print(f"❌ Missing required fields: {missing_fields}")
        return False
    
    # Validate OpenAPI version
    if not spec['openapi'].startswith('3.'):
        print(f"❌ Unsupported OpenAPI version: {spec['openapi']}")
        return False
    
    # Validate info section
    info = spec.get('info', {})
    required_info_fields = ['title', 'version']
    missing_info = [field for field in required_info_fields if field not in info]
    
    if missing_info:
        print(f"❌ Missing required info fields: {missing_info}")
        return False
    
    # Count endpoints
    paths = spec.get('paths', {})
    endpoint_count = sum(len(methods) for methods in paths.values() if isinstance(methods, dict))
    
    print(f"✅ OpenAPI spec validation passed")
    print(f"   - OpenAPI version: {spec['openapi']}")
    print(f"   - API title: {info['title']}")
    print(f"   - API version: {info['version']}")
    print(f"   - Total endpoints: {endpoint_count}")
    print(f"   - Total paths: {len(paths)}")
    
    return True


def extract_endpoints(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all endpoints from the OpenAPI spec."""
    endpoints = []
    
    for path, path_item in spec.get('paths', {}).items():
        if not isinstance(path_item, dict):
            continue
            
        for method, operation in path_item.items():
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                endpoint = {
                    'path': path,
                    'method': method.upper(),
                    'operation_id': operation.get('operationId'),
                    'summary': operation.get('summary'),
                    'tags': operation.get('tags', []),
                    'parameters': operation.get('parameters', []),
                    'security': operation.get('security', []),
                    'responses': operation.get('responses', {})
                }
                endpoints.append(endpoint)
    
    return endpoints


def test_endpoint_availability(base_url: str, endpoint: Dict[str, Any], timeout: int = 5) -> Dict[str, Any]:
    """Test if an endpoint is available and responds correctly."""
    url = base_url.rstrip('/') + endpoint['path']
    method = endpoint['method']
    
    # Replace path parameters with test values for basic connectivity test
    test_url = url.replace('{package_name}', 'test-package')
    test_url = test_url.replace('{username}', 'testuser')
    test_url = test_url.replace('{version}', '1.0.0')
    
    try:
        response = requests.request(
            method=method,
            url=test_url,
            timeout=timeout,
            allow_redirects=False
        )
        
        return {
            'success': True,
            'status_code': response.status_code,
            'response_time': response.elapsed.total_seconds(),
            'content_type': response.headers.get('content-type', ''),
            'error': None
        }
    
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'status_code': None,
            'response_time': None,
            'content_type': None,
            'error': 'Timeout'
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'status_code': None,
            'response_time': None,
            'content_type': None,
            'error': 'Connection Error'
        }
    except Exception as e:
        return {
            'success': False,
            'status_code': None,
            'response_time': None,
            'content_type': None,
            'error': str(e)
        }


def test_api_endpoints(base_url: str, endpoints: List[Dict[str, Any]], max_endpoints: int = None) -> Dict[str, Any]:
    """Test API endpoints for basic connectivity."""
    print(f"\n🧪 Testing API endpoints at {base_url}")
    
    if max_endpoints:
        endpoints = endpoints[:max_endpoints]
        print(f"   Testing first {max_endpoints} endpoints...")
    
    results = {
        'total': len(endpoints),
        'success': 0,
        'failed': 0,
        'details': []
    }
    
    for i, endpoint in enumerate(endpoints, 1):
        path = endpoint['path']
        method = endpoint['method']
        
        print(f"   [{i:2}/{len(endpoints)}] {method:6} {path:<40}", end=" ")
        
        result = test_endpoint_availability(base_url, endpoint)
        
        if result['success']:
            status = result['status_code']
            time_ms = int(result['response_time'] * 1000)
            
            if status < 500:  # Not a server error
                print(f"✅ {status} ({time_ms}ms)")
                results['success'] += 1
            else:
                print(f"⚠️  {status} ({time_ms}ms)")
                results['failed'] += 1
        else:
            print(f"❌ {result['error']}")
            results['failed'] += 1
        
        results['details'].append({
            'endpoint': f"{method} {path}",
            'result': result
        })
    
    success_rate = (results['success'] / results['total']) * 100 if results['total'] > 0 else 0
    
    print(f"\n📊 Test Results:")
    print(f"   ✅ Successful: {results['success']}")
    print(f"   ❌ Failed: {results['failed']}")
    print(f"   📈 Success Rate: {success_rate:.1f}%")
    
    return results


def generate_postman_collection(spec: Dict[str, Any], output_path: str) -> None:
    """Generate a Postman collection from the OpenAPI spec."""
    print(f"\n📄 Generating Postman collection...")
    
    collection = {
        "info": {
            "name": spec['info']['title'],
            "description": spec['info'].get('description', ''),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [],
        "variable": [
            {
                "key": "baseUrl",
                "value": "http://localhost:8000",
                "type": "string"
            }
        ]
    }
    
    # Group endpoints by tags
    tag_groups = {}
    
    for path, path_item in spec.get('paths', {}).items():
        if not isinstance(path_item, dict):
            continue
            
        for method, operation in path_item.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue
                
            tags = operation.get('tags', ['Default'])
            tag = tags[0] if tags else 'Default'
            
            if tag not in tag_groups:
                tag_groups[tag] = []
            
            # Create Postman request item
            request_item = {
                "name": operation.get('summary', f"{method.upper()} {path}"),
                "request": {
                    "method": method.upper(),
                    "header": [],
                    "url": {
                        "raw": f"{{{{baseUrl}}}}{path}",
                        "host": ["{{baseUrl}}"],
                        "path": path.strip('/').split('/') if path != '/' else []
                    }
                },
                "response": []
            }
            
            # Add authentication if required
            if operation.get('security'):
                request_item['request']['auth'] = {
                    "type": "bearer",
                    "bearer": [
                        {
                            "key": "token",
                            "value": "{{accessToken}}",
                            "type": "string"
                        }
                    ]
                }
            
            tag_groups[tag].append(request_item)
    
    # Convert tag groups to Postman folders
    for tag, requests in tag_groups.items():
        folder = {
            "name": tag,
            "item": requests
        }
        collection['item'].append(folder)
    
    # Write collection to file
    with open(output_path, 'w') as f:
        json.dump(collection, f, indent=2)
    
    print(f"✅ Postman collection saved to {output_path}")


def generate_curl_examples(spec: Dict[str, Any], output_path: str) -> None:
    """Generate curl command examples for each endpoint."""
    print(f"\n📄 Generating curl examples...")
    
    examples = []
    base_url = "http://localhost:8000"
    
    for path, path_item in spec.get('paths', {}).items():
        if not isinstance(path_item, dict):
            continue
            
        for method, operation in path_item.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue
            
            # Build curl command
            test_path = path.replace('{package_name}', 'test-package')
            test_path = test_path.replace('{username}', 'testuser')
            test_path = test_path.replace('{version}', '1.0.0')
            
            curl_cmd = [f"curl -X {method.upper()}"]
            
            # Add authentication if required
            if operation.get('security'):
                curl_cmd.append('-H "Authorization: Bearer $ACCESS_TOKEN"')
            
            # Add content type for POST requests
            if method.upper() in ['POST', 'PUT', 'PATCH']:
                curl_cmd.append('-H "Content-Type: application/json"')
            
            curl_cmd.append(f'"{base_url}{test_path}"')
            
            example = {
                'endpoint': f"{method.upper()} {path}",
                'summary': operation.get('summary', ''),
                'curl': ' \\\n  '.join(curl_cmd)
            }
            examples.append(example)
    
    # Write examples to file
    with open(output_path, 'w') as f:
        f.write("# AgentHub Registry API - Curl Examples\n\n")
        
        for example in examples:
            f.write(f"## {example['endpoint']}\n")
            if example['summary']:
                f.write(f"{example['summary']}\n\n")
            f.write(f"```bash\n{example['curl']}\n```\n\n")
    
    print(f"✅ Curl examples saved to {output_path}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Validate and test AgentHub Registry API specification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_api_spec.py                    # Validate spec only
  python scripts/validate_api_spec.py --test-api         # Test API endpoints
  python scripts/validate_api_spec.py --generate-all     # Generate all outputs
  python scripts/validate_api_spec.py --base-url http://localhost:8000 --test-api
        """
    )
    
    parser.add_argument(
        '--spec-file', '-s',
        default='api-spec.yaml',
        help='Path to OpenAPI specification file (default: api-spec.yaml)'
    )
    
    parser.add_argument(
        '--base-url', '-u',
        default='http://localhost:8000',
        help='Base URL for API testing (default: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--test-api', '-t',
        action='store_true',
        help='Test API endpoints for connectivity'
    )
    
    parser.add_argument(
        '--max-endpoints',
        type=int,
        help='Maximum number of endpoints to test'
    )
    
    parser.add_argument(
        '--generate-postman',
        help='Generate Postman collection (specify output path)'
    )
    
    parser.add_argument(
        '--generate-curl',
        help='Generate curl examples (specify output path)'
    )
    
    parser.add_argument(
        '--generate-all',
        action='store_true',
        help='Generate all output files (Postman collection and curl examples)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='docs/api',
        help='Output directory for generated files (default: docs/api)'
    )
    
    args = parser.parse_args()
    
    print("🚀 AgentHub Registry API Specification Validator")
    print("=" * 60)
    
    # Check if spec file exists
    if not Path(args.spec_file).exists():
        print(f"❌ API specification file not found: {args.spec_file}")
        sys.exit(1)
    
    # Load and validate specification
    spec = load_api_spec(args.spec_file)
    
    if not validate_openapi_spec(spec):
        sys.exit(1)
    
    # Create output directory if needed
    if args.generate_all or args.generate_postman or args.generate_curl:
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Test API endpoints
    if args.test_api:
        endpoints = extract_endpoints(spec)
        results = test_api_endpoints(args.base_url, endpoints, args.max_endpoints)
        
        if results['failed'] > 0:
            print(f"\n⚠️  Some endpoints failed connectivity tests")
    
    # Generate outputs
    if args.generate_all or args.generate_postman:
        output_path = args.generate_postman or f"{args.output_dir}/agenthub-registry.postman_collection.json"
        generate_postman_collection(spec, output_path)
    
    if args.generate_all or args.generate_curl:
        output_path = args.generate_curl or f"{args.output_dir}/curl-examples.md"
        generate_curl_examples(spec, output_path)
    
    print(f"\n✅ API specification validation completed successfully!")


if __name__ == "__main__":
    main() 