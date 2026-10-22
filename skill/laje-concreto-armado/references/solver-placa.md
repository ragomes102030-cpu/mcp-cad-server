# Solver de placas (biharmônico de 13 pontos) — validado

Serve para laje **maciça** em grelha, apoiada em vigas nos quatro lados (bordas
engastadas) ou com borda livre. Resolve `nabla^4 w = q/D` por diferencas finitas e
devolve os momentos por metro de largura.

## Stencil

```
        +1
      2   2
-8  -8  20  -8  -8
      2   2
        +1
```
Soma = `20w0 - 8(N+S+L+O) + 2(4 diagonais) + 1(4 nos a +/-2)` = `q a^4 / D`

**O sinal do termo +/-2 e `+1`.** Com `-1` (o erro mais comum) a solucao sai ~1e4 vezes
menor e os momentos vem absurdamente baixos sem avisar.

## Contorno engastado (o erro que custa 15 %)

- `w = 0` **apenas no no 0** (e no no `n-1` do outro lado).
- Nos interiores: `i` de `1` a `n-2`.
- **Fantasma:** `w[-1] = w[1]` e `w[n] = w[n-2]` - e isso que impoe `dw/dn = 0`.
  Tratar o anel mais externo como parede (`w=0` em `i=0` e `i=1`) **subtrai 15 % do
  momento no apoio** e nenhum render mostra isso.

## Momento no apoio: extrapolacao quadratica

O no `i=1` esta em `x=a`, **nao** no apoio. O momento perto do apoio varia quadraticamente
(`M(x) = M0 + V x - q x^2/2`), entao:

```
M(0) = 3*M1 - 3*M2 + M3        # Lagrange sobre x=a, 2a, 3a
```

Sem isso o momento negativo sai entre 15 % e 25 % baixo, e a armadura negativa
fica subdimensionada.

## Codigo (numpy, sem scipy)

```python
NB = [(-1,0,-8),(1,0,-8),(0,-1,-8),(0,1,-8),(-1,-1,2),(-1,1,2),(1,-1,2),(1,1,2),
      (-2,0,1),(2,0,1),(0,-2,1),(0,2,1)]

def solve(a, Lx, Ly, qval, nu=0.2):
    """qval em kN/m2. Devolve W com w em unidades de D=1."""
    nx, ny = int(round(Lx/a))+1, int(round(Ly/a))+1
    nxi, nyi = nx-2, ny-2
    II, JJ = np.meshgrid(np.arange(1,nx-1), np.arange(1,ny-1), indexing='ij')
    I, J = II.ravel(), JJ.ravel()
    n = nxi*nyi
    A = np.zeros((n, n)); b = np.full(n, qval*a**4)
    gid = lambda i, j: (i-1)*nyi + (j-1)
    for k in range(n):
        i, j = I[k], J[k]; A[k, gid(i,j)] = 20
        for di, dj, c in NB:
            ii, jj = i+di, j+dj
            if   1 <= ii <= nx-2 and 1 <= jj <= ny-2: A[k, gid(ii,jj)] += c
            elif ii == -1:  A[k, gid(1,jj)]    += c   # fantasma i=-1  -> w[1]
            elif ii == nx:  A[k, gid(nx-2,jj)] += c   # fantasma i=nx  -> w[nx-2]
            elif jj == -1:  A[k, gid(ii,1)]    += c
            elif jj == ny:  A[k, gid(ii,ny-2)] += c
    W = np.zeros((nx, ny)); W[1:nx-1, 1:ny-1] = np.linalg.solve(A, b).reshape(nxi, nyi)
    return W

def shf(W, dI, dJ):                       # shift com borda zerada
    r = np.zeros_like(W)
    i0, i1 = max(0,dI), W.shape[0]+min(0,dI)
    j0, j1 = max(0,dJ), W.shape[1]+min(0,dJ)
    r[i0:i1, j0:j1] = W[i0-dI:i1-dI, j0-dJ:j1-dJ]
    return r

def momentos(W, a, nu=0.2):
    c2x = (shf(W,1,0) - 2*W + shf(W,-1,0)) / a**2
    c2y = (shf(W,0,1) - 2*W + shf(W,0,-1)) / a**2
    return -(c2x + nu*c2y), -(c2y + nu*c2x)     # Mx, My  em kN.m/m

def M_sup(M, i0, j):                          # momento no apoio (x=0), extrapolado
    return 3*M[i0,j] - 3*M[i0+1,j] + M[i0+2,j]
```

## Validacao obrigatoria (rode antes de confiar em qualquer numero)

| Caso | q | Malha | Calculado | Referencia |
|---|---|---|---|---|
| Uma-via `2,00 x 20,00 m` | 8,4 | 0,05 m | M+ = 1,4018 / M- = -2,7983 | 1,400 / -2,800 |
| Quadrada `4,00 x 4,00 m` | 8,4 | 0,05 m | M- = -0,05128*qL^2 | -0,0513 (Timoshenko) |

Sem essas duas linhas verdes, **nao use o solver**.

## Leitura dos resultados

`W` sai em unidades de `D = 1`. Para obter a flecha real:

```
D      = E h^3 / (12 (1 - nu^2))      # E = 5600 sqrt(fck)  (MPa)
w_real = w_codigo * (q_SI / D) / q_codigo
```

com `q_SI` em N/m2 e `q_codigo` em kN/m2. (Os momentos **nao** precisam disso: com `D=1`
a formula `M = -(kx + nu ky)` ja devolve kN.m/m.)

## Convergencia

Momentos de centro convergem rapido (< 0,3 % entre 0,10 m e 0,05 m). **Nos apoios
converge devagar** - use duas malhas e extrapole por Richardson
(`valor + (valor_fino - valor_grosso)/3`). Se a diferenca passar de 5 %, registre a
incerteza no relatorio em vez de fingir que convergiu.
