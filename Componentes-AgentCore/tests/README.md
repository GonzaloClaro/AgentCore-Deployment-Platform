# Tests de Componentes-AgentCore

Tests para los scripts Python que ejecutan los componentes CI.

## Cómo correr

```bash
cd Componentes-AgentCore
pip install -r src/requirements.txt pytest pyyaml jsonschema
pytest tests/
```

## Estructura

```
tests/
├── conftest.py           # fixtures compartidas (paths, composition_map, etc.)
├── fixtures/             # YAMLs/JSONs de prueba
│   ├── composition_map.yml
│   └── manifest_valid.yaml
└── unit/                 # tests por componente
    ├── test_validate_structure.py
    ├── test_render_tfvars.py    # TODO
    ├── test_validate_manifest.py # TODO
    └── test_apply_policy.py     # TODO
```

## Niveles de test (objetivo)

1. **Unit (este directorio)**: scripts Python individuales con fixtures.
2. **Schema**: que los manifests de `_template/` pasen el JSON-schema.
3. **Structural**: que `composition_map.yml` referencie módulos existentes
   en `Infra-AgentCore/modules/`, y composiciones existentes en `compositions/`.
4. **Integration**: render_tfvars + validate_structure + apply_policy en
   secuencia con un manifest sandbox completo.
5. **Terraform**: `terraform validate` + `terraform fmt -check` en cada módulo
   y composición (separado, en `Infra-AgentCore/tests/`).

## Lo que ya cubrimos

- ✅ validate_structure: 7 casos (composition válida, requires faltantes,
  cedar files, inline policies, tool lambda, gateway custom warning).

## TODO de tests

- [ ] render_tfvars: verificar que con un manifest X produce tfvars JSON Y
- [ ] apply_policy: verificar lectura de .cedar files
- [ ] validate_manifest: verificar que el JSON-schema rechaza casos malformados
- [ ] Terraform validate sobre cada módulo (con `terraform test` framework)
- [ ] Test integración: pipeline completo en sandbox
