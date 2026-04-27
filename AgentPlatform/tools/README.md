# tools/

Librerías Python compartidas que múltiples agentes / MCPs pueden importar (helpers de auth, logging estructurado, clientes de Bedrock con retry, etc.).

Por simplicidad inicial los workloads importan estas tools por **path local** (vía `requirements.txt` con `-e ../../tools/<name>`). Si crece, migrar a CodeArtifact.

## Convenciones

```
tools/
  shared-{name}/
    src/{name}/__init__.py
    pyproject.toml
    README.md
    tests/
```
