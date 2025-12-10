"""
Exemplo de sincronização de contas entre si.

Este exemplo demonstra como sincronizar todas as contas carregadas
no AccountManager, garantindo que cada conta tenha todas as outras
como contatos.
"""

from zowsuplib.app.account_manager import AccountManager
from loguru import logger
import time


def main():
    # Obtém o gerenciador
    manager = AccountManager.get_instance()
    
    logger.info("=== Exemplo: Sincronizar todas as contas entre si ===")
    
    # 1. Carrega todas as contas importadas (sem conectar)
    logger.info("\n1. Carregando todas as contas importadas...")
    clients = manager.load_all_imported_accounts(
        auto_connect=False,
        only_initialized=True  # Apenas contas inicializadas
    )
    
    if not clients:
        logger.warning("Nenhuma conta carregada. Importe contas primeiro.")
        return
    
    logger.info(f"Contas carregadas: {len(clients)}")
    for phone in clients.keys():
        logger.info(f"  - {phone}")
    
    # 2. Conecta todas as contas
    logger.info("\n2. Conectando todas as contas...")
    connected_count = 0
    for phone, client in clients.items():
        try:
            if not client.is_connected():
                logger.info(f"Conectando conta {phone}...")
                client.connect(wait_login=True)
                if client.is_connected():
                    connected_count += 1
                    logger.info(f"  ✓ {phone} conectada")
                else:
                    logger.warning(f"  ✗ {phone} falhou ao conectar")
            else:
                connected_count += 1
                logger.info(f"  ✓ {phone} já estava conectada")
        except Exception as e:
            logger.error(f"  ✗ Erro ao conectar {phone}: {e}")
    
    logger.info(f"Total de contas conectadas: {connected_count}/{len(clients)}")
    
    if connected_count < 2:
        logger.warning("É necessário pelo menos 2 contas conectadas para sincronização")
        return
    
    # 3. Aguarda um pouco para estabilizar
    logger.info("\n3. Aguardando 3 segundos para estabilizar conexões...")
    time.sleep(3)
    
    # 4. Sincroniza todas as contas entre si
    logger.info("\n4. Sincronizando todas as contas entre si...")
    stats = manager.sync_all_accounts(
        sync_delay=0.5,  # Delay de 0.5s entre sincronizações
        only_connected=True  # Apenas contas conectadas
    )
    
    # 5. Exibe estatísticas
    logger.info("\n5. Estatísticas da sincronização:")
    logger.info(f"  Total de contas: {stats['total_accounts']}")
    logger.info(f"  Contas sincronizadas: {stats['synced_accounts']}")
    logger.info(f"  Contas puladas: {stats['skipped_accounts']}")
    logger.info(f"  Total de sincronizações: {stats['total_syncs']}")
    logger.info(f"  Sincronizações bem-sucedidas: {stats['successful_syncs']}")
    logger.info(f"  Sincronizações falhadas: {stats['failed_syncs']}")
    
    logger.info("\n6. Detalhes por conta:")
    for phone, details in stats['details'].items():
        status_icon = "✓" if details['status'] == 'success' else "⚠" if details['status'] == 'partial' else "✗"
        logger.info(
            f"  {status_icon} {phone}: "
            f"{details['synced_count']}/{details.get('total_attempted', 0)} contatos sincronizados "
            f"({details['status']})"
        )
    
    # 6. Exemplo: Sincronizar com delay maior
    logger.info("\n=== Exemplo: Sincronizar com delay maior ===")
    stats2 = manager.sync_all_accounts(
        sync_delay=1.0,  # Delay de 1 segundo
        only_connected=True
    )
    logger.info(f"Sincronização com delay maior: {stats2['successful_syncs']} sucessos")
    
    # 7. Exemplo: Excluir algumas contas da sincronização
    logger.info("\n=== Exemplo: Sincronizar excluindo algumas contas ===")
    if len(clients) > 2:
        # Exclui a primeira conta da sincronização
        exclude_phones = [list(clients.keys())[0]]
        logger.info(f"Excluindo contas: {exclude_phones}")
        
        stats3 = manager.sync_all_accounts(
            sync_delay=0.5,
            only_connected=True,
            exclude_phones=exclude_phones
        )
        logger.info(f"Sincronização com exclusões: {stats3['successful_syncs']} sucessos")
    
    logger.info("\n=== Sincronização concluída ===")
    
    # Mantém as contas conectadas por um tempo
    logger.info("\nMantendo contas conectadas. Pressione Ctrl+C para desconectar e sair.")
    try:
        while True:
            time.sleep(60)
            # Verifica status das conexões
            connected = sum(1 for c in clients.values() if c.is_connected())
            logger.info(f"Contas conectadas: {connected}/{len(clients)}")
    except KeyboardInterrupt:
        logger.info("\nDesconectando todas as contas...")
        manager.disconnect_all()
        logger.info("Todas as contas desconectadas.")


if __name__ == "__main__":
    main()



