"""Regression coverage for V4 DXF-native detailing and PDF A3 sheet."""
import json
from pathlib import Path

import ezdxf
import pytest

from mcp_cad_cloud.multifamiliar_arch_v4 import (
    _room_program, generate_multifamily_v4, ArchitecturalDetailError
)

def test_four_units_and_brutal_areas_are_flagged_gross():
    rooms=_room_program()
    assert len(rooms)==20
    assert {r.uid for r in rooms}=={'AP01','AP02','AP03','AP04'}
    for uid in ('AP01','AP02','AP03','AP04'):
        unit=[r for r in rooms if r.uid==uid]
        assert len(unit)==5
        assert sum(r.gross_area for r in unit)==pytest.approx(94.8)

def test_v4_is_real_dxf_and_same_a3_pdf(tmp_path):
    result=generate_multifamily_v4(tmp_path)
    assert result['status']=='v4_detailed_preliminary_not_normatively_approved'
    doc=ezdxf.readfile(result['dxf'])
    assert not doc.audit().has_errors
    assert 'ARQ-01 A3 REV04' in doc.layouts
    m=doc.modelspace()
    assert len(m.query('ARC'))==21
    assert len([e for e in m.query('TEXT') if e.dxf.layer=='ARQ-AREAS'])==20
    assert len([e for e in m.query('LINE') if e.dxf.layer=='ARQ-COTAS-INTERNAS'])>=20
    assert len([e for e in m.query('SOLID') if e.dxf.layer=='ARQ-SIMBOLOS'])==1
    audit=json.loads(Path(result['audit']).read_text())
    assert audit['unit_count']==4
    assert audit['additional_fixture_count']==20
    assert audit['furniture_collision_errors']==[]
    assert audit['dxf_audit_errors']==0
    assert audit['area_basis'].find('NOT usable')>=0
    fitz=pytest.importorskip('fitz')
    with fitz.open(result['pdf']) as document:
        assert len(document)==1
        p=document[0]
        assert p.rect.width==pytest.approx(420/25.4*72,abs=1)
        assert p.rect.height==pytest.approx(297/25.4*72,abs=1)
        content=p.get_text()
        assert 'REVISAO 04' in content
        assert 'NAO UTILIZAR PARA EXECUCAO' in content
        assert 'ESCADA: DIMENSIONAMENTO PENDENTE' in content

def test_invalid_v3_base_is_rejected(tmp_path):
    invalid=ezdxf.new()
    path=tmp_path/'invalid.dxf'
    invalid.saveas(path)
    with pytest.raises(ArchitecturalDetailError,match='Base V3'):
        generate_multifamily_v4(tmp_path/'out',base_dxf=path)
