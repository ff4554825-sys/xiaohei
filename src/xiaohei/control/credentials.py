from typing import List, Dict, List, Optional
from uuid import UUID
from loguru import logger

from ..types import Credential, ProviderType


class CredentialPool:
    def __init__(self):
        self._credentials: Dict[UUID, Credential] = {}
        self._provider_index: Dict[ProviderType, List[UUID]] = {}
        logger.info("CredentialPool initialized")

    def add_credential(self, credential: Credential) -> None:
        self._credentials[credential.id] = credential

        if credential.provider not in self._provider_index:
            self._provider_index[credential.provider] = []
        self._provider_index[credential.provider].append(credential.id)

        logger.info(f"Credential added for provider: {credential.provider}")

    def get_credential(self, credential_id: UUID) -> Optional[Credential]:
        return self._credentials.get(credential_id)

    def get_credentials_by_provider(self, provider: ProviderType) -> List[Credential]:
        ids = self._provider_index.get(provider, [])
        return [self._credentials[id] for id in ids if self._credentials[id].enabled]

    def get_active_credential(self, provider: ProviderType) -> Optional[Credential]:
        credentials = self.get_credentials_by_provider(provider)
        if credentials:
            return credentials[0]
        return None

    def remove_credential(self, credential_id: UUID) -> bool:
        credential = self._credentials.get(credential_id)
        if credential:
            del self._credentials[credential_id]

            if credential.provider in self._provider_index:
                self._provider_index[credential.provider].remove(credential_id)

            logger.info(f"Credential removed: {credential_id}")
            return True
        return False

    def list_credentials(self) -> List[Credential]:
        return list(self._credentials.values())

    def enable_credential(self, credential_id: UUID) -> bool:
        credential = self._credentials.get(credential_id)
        if credential:
            credential.enabled = True
            logger.info(f"Credential enabled: {credential_id}")
            return True
        return False

    def disable_credential(self, credential_id: UUID) -> bool:
        credential = self._credentials.get(credential_id)
        if credential:
            credential.enabled = False
            logger.info(f"Credential disabled: {credential_id}")
            return True
        return False

    def has_credentials(self, provider: ProviderType) -> bool:
        return len(self.get_credentials_by_provider(provider)) > 0
