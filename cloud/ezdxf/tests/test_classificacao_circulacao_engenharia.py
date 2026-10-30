"""Independent engineering classification must never claim architectural approval."""
from copy import deepcopy

from test_auditoria_circulacao import drawing as drawing_fixture
from mcp_cad_cloud.auditoria_circulacao import auditar_circulacao


def test_valid_connection_still_has_explicit_non_normative_classification():
    model,doc=drawing_fixture.__wrapped__()
    result=auditar_circulacao(model,doc)
    assert result["ok"] is True
    classification=result["classificacao"]
    assert classification["aprovacao_arquitetonica"] is False
    assert classification["verificacao_normativa"] == "NAO_REALIZADA"
    assert "NBR 9050" in " ".join(classification["informacoes_insuficientes"])
    assert classification["status_geometrico"] == "sem_erro_detectado_nas_verificacoes_executadas"


def test_blocked_entry_is_functional_failure_not_automatic_geometry_invalidity():
    model,doc=drawing_fixture.__wrapped__()
    doc.modelspace().add_lwpolyline(
        [(.42,.15),(1.48,.15),(1.48,.78),(.42,.78)],
        close=True,dxfattribs={"layer":"MOBILIARIO"})
    result=auditar_circulacao(model,doc)
    assert not result["ok"]
    classification=result["classificacao"]
    assert classification["status_funcional"]=="erro"
    assert "porta-colide-mobiliario" in [
        item["chave"] for item in classification["problemas_funcionais"]]
    assert classification["aprovacao_arquitetonica"] is False


def test_bad_door_count_is_geometry_class_and_does_not_hide_other_findings():
    model,doc=drawing_fixture.__wrapped__()
    model=deepcopy(model)
    doc.modelspace().delete_entity(
        next(iter(doc.modelspace().query('ARC[layer=="PORTAS"]'))))
    result=auditar_circulacao(model,doc)
    classification=result["classificacao"]
    assert classification["status_geometrico"]=="erro"
    assert "portas-incompletas" in [
        item["chave"] for item in classification["erros_geometricos"]]
    assert classification["verificacao_normativa"]=="NAO_REALIZADA"
