"""
Exemplo de exportação de contatos para formato vCard.

Este exemplo demonstra como exportar todos os contatos de uma conta
WhatsApp para o formato vCard (.vcf), que pode ser importado em
aplicativos de contatos como Google Contacts, Apple Contacts, etc.
"""

from app.account_manager import AccountManager
from loguru import logger
import os


def main():
    # Obtém o gerenciador
    manager = AccountManager.get_instance()
    
    # Número da conta para exportar contatos
    account_phone = "5511999999999"  # Substitua pelo número da sua conta
    
    logger.info(f"=== Exportando contatos da conta {account_phone} ===")
    
    # Adiciona a conta (não precisa estar conectada para exportar)
    try:
        client = manager.add_account(account_phone, env="smb_android", auto_connect=False)
        logger.info(f"Conta {account_phone} carregada")
    except Exception as e:
        logger.error(f"Erro ao carregar conta: {e}")
        return
    
    # Exporta contatos para arquivo vCard
    output_file = f"contacts_{account_phone}.vcf"
    
    try:
        logger.info("Exportando contatos para vCard...")
        result = client.export_contacts_to_vcard(
            output_file=output_file,
            include_groups=False  # Não inclui grupos na exportação
        )
        
        logger.info(f"Contatos exportados com sucesso para: {result}")
        
        # Verifica o tamanho do arquivo
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            logger.info(f"Tamanho do arquivo: {file_size} bytes")
            
            # Lê algumas linhas para mostrar o conteúdo
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:20]  # Primeiras 20 linhas
                logger.info("Primeiras linhas do arquivo vCard:")
                for line in lines:
                    logger.info(f"  {line.rstrip()}")
        
    except Exception as e:
        logger.error(f"Erro ao exportar contatos: {e}", exc_info=True)
    
    # Exemplo: Exportar apenas para string (sem salvar arquivo)
    try:
        logger.info("\n=== Exportando para string ===")
        vcard_content = client.export_contacts_to_vcard()
        
        if vcard_content:
            logger.info(f"Conteúdo vCard gerado ({len(vcard_content)} caracteres)")
            # Mostra as primeiras 500 caracteres
            preview = vcard_content[:500]
            logger.info(f"Preview:\n{preview}...")
        else:
            logger.warning("Nenhum contato encontrado para exportar")
            
    except Exception as e:
        logger.error(f"Erro ao exportar para string: {e}", exc_info=True)
    
    # Exemplo: Exportar incluindo grupos
    try:
        logger.info("\n=== Exportando incluindo grupos ===")
        output_file_groups = f"contacts_with_groups_{account_phone}.vcf"
        result = client.export_contacts_to_vcard(
            output_file=output_file_groups,
            include_groups=True
        )
        logger.info(f"Contatos e grupos exportados para: {result}")
    except Exception as e:
        logger.error(f"Erro ao exportar com grupos: {e}", exc_info=True)


if __name__ == "__main__":
    main()

