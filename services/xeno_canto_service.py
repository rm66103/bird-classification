"""
Xeno-canto API Service

This service provides an interface to the Xeno-canto public API v3 for retrieving
bird call recording metadata. It handles API queries, pagination, and returns
structured JSON data from the API.

API Documentation: https://xeno-canto.org/explore/api

Note: API v3 requires an API key. Get your key from your Xeno-canto account page
after registering and verifying your email address.
"""

import requests
from typing import Dict, List, Optional, Any
import os


class XenoCantoService:
    """Service for interacting with the Xeno-canto API v3."""
    
    BASE_URL = "https://xeno-canto.org/api/3/"
    RECORDINGS_ENDPOINT = "recordings"
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize the Xeno-canto service.
        
        Args:
            api_key: Xeno-canto API key (required for v3). If not provided,
                    will attempt to read from XENO_CANTO_API_KEY environment variable.
            timeout: Request timeout in seconds (default: 30)
        
        Raises:
            ValueError: If no API key is provided and not found in environment
        """
        self.api_key = api_key or os.getenv('XENO_CANTO_API_KEY')
        if not self.api_key:
            raise ValueError(
                "API key is required for Xeno-canto API v3. "
                "Provide it as a parameter or set XENO_CANTO_API_KEY environment variable. "
                "Get your key from: https://xeno-canto.org/explore/api"
            )
        
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'bird-classification-project/1.0'
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Make a GET request to the Xeno-canto API v3.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters (API key will be added automatically)
            
        Returns:
            JSON response as dictionary, or None if request fails
        """
        # Construct URL explicitly to avoid urljoin quirks
        base = self.BASE_URL.rstrip('/')
        endpoint_clean = endpoint.lstrip('/')
        url = f"{base}/{endpoint_clean}"
        
        # Ensure API key is included in params
        if params is None:
            params = {}
        params['key'] = self.api_key
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
    
    def search_recordings(
        self,
        species_scientific_name: Optional[str] = None,
        species_common_name: Optional[str] = None,
        quality: Optional[str] = None,
        country: Optional[str] = None,
        since: Optional[str] = None,
        page: int = 1,
        per_page: Optional[int] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Search for recordings using various filters (API v3).
        
        Args:
            species_scientific_name: Scientific name (e.g., "Turdus migratorius")
            species_common_name: Common name (e.g., "American Robin")
            quality: Recording quality filter (e.g., "A", "B", ">C")
            country: Country code (e.g., "US", "CA")
            since: Date filter (e.g., "2020-01-01" or "31" for last 31 days)
            page: Page number for pagination (default: 1)
            per_page: Results per page (50-500, default: 100)
            **kwargs: Additional query parameters using API v3 search tags
            
        Returns:
            API response dictionary with recordings and metadata, or None if request fails
        """
        query_parts = []
        
        if species_scientific_name:
            # Use gen and sp tags for scientific name (v3 format)
            # If full scientific name provided, split into genus and species
            parts = species_scientific_name.split(maxsplit=1)
            if len(parts) == 2:
                query_parts.append(f'gen:{parts[0]} sp:{parts[1]}')
            else:
                query_parts.append(f'sci:"{species_scientific_name}"')
        
        if species_common_name:
            # API v3 uses 'en:' tag for English/common names
            # Use quotes for multi-word names, no quotes for single words
            if ' ' in species_common_name:
                query_parts.append(f'en:"{species_common_name}"')
            else:
                query_parts.append(f'en:{species_common_name}')
        
        if quality:
            query_parts.append(f'q:{quality}')
        
        if country:
            # Use quotes for multi-word country names, no quotes for single words
            if ' ' in country:
                query_parts.append(f'cnt:"{country}"')
            else:
                query_parts.append(f'cnt:{country}')
        
        if since:
            query_parts.append(f'since:{since}')
        
        # Add any additional query parameters (should use v3 search tags)
        for key, value in kwargs.items():
            if value:
                # Quote only if value contains spaces
                if ' ' in str(value):
                    query_parts.append(f'{key}:"{value}"')
                else:
                    query_parts.append(f'{key}:{value}')
        
        # API v3 uses spaces to join query terms (not +)
        query_string = " ".join(query_parts) if query_parts else ""
        
        if not query_string:
            raise ValueError("At least one search parameter is required for API v3")
        
        params = {
            'query': query_string,
            'page': page
        }
        
        if per_page is not None:
            if not (50 <= per_page <= 500):
                raise ValueError("per_page must be between 50 and 500")
            params['per_page'] = per_page
        
        return self._make_request(self.RECORDINGS_ENDPOINT, params=params)
    
    def get_all_recordings_for_species(
        self,
        species_scientific_name: Optional[str] = None,
        species_common_name: Optional[str] = None,
        quality: Optional[str] = None,
        max_recordings: Optional[int] = None,
        per_page: int = 100,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all recordings for a species, handling pagination automatically.
        
        Args:
            species_scientific_name: Scientific name of the species
            species_common_name: Common name of the species
            quality: Quality filter (e.g., ">C" for quality better than C)
            max_recordings: Maximum number of recordings to retrieve (None for all)
            per_page: Results per page (50-500, default: 100)
            **kwargs: Additional query parameters
            
        Returns:
            List of recording dictionaries
        """
        all_recordings = []
        page = 1
        
        while True:
            response = self.search_recordings(
                species_scientific_name=species_scientific_name,
                species_common_name=species_common_name,
                quality=quality,
                page=page,
                per_page=per_page,
                **kwargs
            )
            
            if not response:
                break
            
            recordings = response.get('recordings', [])
            if not recordings:
                break
            
            all_recordings.extend(recordings)
            
            # Check if we've reached the maximum
            if max_recordings and len(all_recordings) >= max_recordings:
                all_recordings = all_recordings[:max_recordings]
                break
            
            # Check if there are more pages (API v3 uses numPages)
            num_pages = response.get('numPages', 1)
            if page >= num_pages:
                break
            
            page += 1
        
        return all_recordings
    
    def get_recording_by_id(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific recording by its ID (API v3).
        
        Args:
            recording_id: The Xeno-canto recording ID
            
        Returns:
            Recording dictionary, or None if not found
        """
        params = {'query': f'id:{recording_id}'}
        response = self._make_request(self.RECORDINGS_ENDPOINT, params=params)
        
        if response and response.get('recordings'):
            return response['recordings'][0]
        
        return None
    
    def get_species_info(self, species_scientific_name: str) -> Optional[Dict[str, Any]]:
        """
        Get summary information about a species (total recordings, etc.).
        
        Args:
            species_scientific_name: Scientific name of the species
            
        Returns:
            API response with species information, or None if request fails
        """
        return self.search_recordings(
            species_scientific_name=species_scientific_name,
            page=1
        )