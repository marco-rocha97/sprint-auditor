from sprint_auditor.demo_pipeline import executar_demo, main


class TestExecutarDemo:
    """Testes de integração do ponto de entrada executar_demo"""

    def test_pipeline_completo_executa_sem_excecao(self):
        """executar_demo() retorna string não vazia sem levantar exceção"""
        resultado = executar_demo()

        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_output_contem_secoes_dos_3_updates(self):
        """Output contém "Update #1", "Update #2" e "Update #3" """
        resultado = executar_demo()

        assert "Update #1" in resultado
        assert "Update #2" in resultado
        assert "Update #3" in resultado

    def test_update_1_esta_no_trilho(self):
        """Update #1 está no trilho — output contém "no trilho" após o Update #1"""
        resultado = executar_demo()

        assert "no trilho" in resultado

    def test_alerta_desvio_limiar_presente_no_update_2(self):
        """Alerta DESVIO_LIMIAR presente no Update #2 (dia 6)"""
        resultado = executar_demo()

        assert "DESVIO_LIMIAR" in resultado
        assert "Dia: 6" in resultado

    def test_alerta_presente_no_update_3(self):
        """Alertas presentes no Update #3 (dia 9)"""
        resultado = executar_demo()

        tem_alerta = (
            "DESVIO" in resultado
            or "BLOQUEIO" in resultado
            or "DETERIORACAO" in resultado
        )
        assert "Update #3" in resultado and tem_alerta

    def test_rastreabilidade_id_artefato_fonte_no_output(self):
        """Rastreabilidade: ID do artefato-fonte no output — procura por 'art-u2-board'"""
        resultado = executar_demo()

        assert "art-u2-board" in resultado

    def test_secao_contraste_presente(self):
        """Seção de contraste presente — output contém "RESUMO DA DEMO" e "Antecipação" """
        resultado = executar_demo()

        assert "RESUMO DA DEMO" in resultado
        assert "Antecipação" in resultado

    def test_contraste_mostra_6_dias_antecipacao(self):
        """Contraste mostra 6 dias de antecipação — output contém "6 dias" """
        resultado = executar_demo()

        assert "6 dias" in resultado

    def test_sem_frase_hardcoded(self):
        """Frase hardcoded foi removida — output não contém 'isso é exatamente' (T07)"""
        resultado = executar_demo()

        assert "isso é exatamente" not in resultado

    def test_quatro_updates_processados(self):
        """Seed agora tem 4 updates — output contém "Update #4" (T07)"""
        resultado = executar_demo()

        assert "Update #4" in resultado


class TestMain:
    """Testes do ponto de entrada main"""

    def test_main_imprime_output_em_stdout(self, capsys):
        """main() imprime o output de executar_demo() em stdout"""
        main()

        capturado = capsys.readouterr()
        assert "SPRINT AUDITOR" in capturado.out
