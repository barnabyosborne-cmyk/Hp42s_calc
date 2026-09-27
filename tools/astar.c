/*
 * astar.c -- the inner loop of route_signals.py, in C.
 *
 * The same search as route_signals.astar(), which stays as the fallback and
 * the reference: two layers of a grid, eight directions per layer, a via
 * between them, a turn penalty taken from the direction a cell was reached
 * from, weighted octile heuristic to the target bounding box. In Python it is
 * about a minute per long net; here it is well under a second, which is what
 * makes rip-up-and-retry affordable.
 *
 * vcost[c] is the cost of a via at cell c, so congestion can price vias too.
 *
 * route_signals.py compiles this itself on first use:
 *     cc -O2 -shared -fPIC -o astar.so astar.c
 */
#include <math.h>
#include <stdint.h>
#include <stdlib.h>

typedef struct { float f; int32_t s; } item;

static item *heap;
static int hn, hcap;

static void push(float f, int32_t s)
{
    if (hn == hcap) {
        hcap = hcap ? hcap * 2 : 1 << 16;
        heap = realloc(heap, sizeof(item) * hcap);
    }
    int i = hn++;
    while (i > 0) {
        int p = (i - 1) / 2;
        if (heap[p].f <= f) break;
        heap[i] = heap[p];
        i = p;
    }
    heap[i].f = f;
    heap[i].s = s;
}

static item pop(void)
{
    item top = heap[0], last = heap[--hn];
    int i = 0;
    for (;;) {
        int c = 2 * i + 1;
        if (c >= hn) break;
        if (c + 1 < hn && heap[c + 1].f < heap[c].f) c++;
        if (heap[c].f >= last.f) break;
        heap[i] = heap[c];
        i = c;
    }
    heap[i] = last;
    return top;
}

static const int DI[8] = {1, 1, 0, -1, -1, -1, 0, 1};
static const int DJ[8] = {0, 1, 1, 1, 0, -1, -1, -1};

int astar(int nx, int ny,
          const uint8_t *openT,      /* 2*N: layer 0 then layer 1 */
          const uint8_t *openV,      /* N */
          const float *cost,         /* 2*N */
          const float *vcost, float turn, float weight, float G,
          const int32_t *src, int nsrc,
          const uint8_t *target,     /* 2*N */
          int ti0, int tj0, int ti1, int tj1,
          int wi0, int wj0, int wi1, int wj1,
          int32_t *out, int max_out)
{
    const int N = nx * ny;
    float *g = malloc(sizeof(float) * 2 * N);
    int32_t *prev = malloc(sizeof(int32_t) * 2 * N);
    int8_t *dir = malloc(2 * N);
    uint8_t *state = calloc(2 * N, 1);     /* 0 unseen, 1 open, 2 done */
    const float diag = G * (float)M_SQRT2;
    int result = -1;
    hn = 0;

#define H(c) ({ int _i = (c) % nx, _j = (c) / nx;                        \
    int _dx = ti0 - _i > 0 ? ti0 - _i : (_i - ti1 > 0 ? _i - ti1 : 0);   \
    int _dy = tj0 - _j > 0 ? tj0 - _j : (_j - tj1 > 0 ? _j - tj1 : 0);   \
    int _mx = _dx > _dy ? _dx : _dy, _mn = _dx > _dy ? _dy : _dx;        \
    weight * G * (_mx + 0.4142f * _mn); })

    for (int k = 0; k < nsrc; k++) {
        int s = src[k];
        g[s] = 0;
        prev[s] = -1;
        dir[s] = -1;
        state[s] = 1;
        push(H(s % N), s);
    }
    while (hn) {
        item it = pop();
        int s = it.s;
        if (state[s] == 2) continue;
        state[s] = 2;
        if (target[s]) {
            int n = 0;
            for (int k = s; k >= 0; k = prev[k]) n++;
            if (n <= max_out) {
                int k = s;
                for (int m = n - 1; m >= 0; m--) { out[m] = k; k = prev[k]; }
                result = n;
            } else {
                result = -2;
            }
            break;
        }
        int L = s / N, c = s % N, i = c % nx, j = c / nx;
        const uint8_t *oT = openT + L * N;
        const float *cm = cost + L * N;
        float gs = g[s];
        int d = dir[s];
        for (int nd = 0; nd < 8; nd++) {
            int ii = i + DI[nd], jj = j + DJ[nd];
            if (ii < wi0 || jj < wj0 || ii > wi1 || jj > wj1) continue;
            int cc = jj * nx + ii;
            if (!oT[cc]) continue;
            int ns = L * N + cc;
            if (state[ns] == 2) continue;
            float ng;
            if (DI[nd] && DJ[nd]) {
                if (!oT[j * nx + ii] || !oT[jj * nx + i]) continue;
                ng = gs + diag * cm[cc];
            } else {
                ng = gs + G * cm[cc];
            }
            if (d >= 0 && nd != d) {
                int t = abs(nd - d) % 8;
                ng += turn * (t < 8 - t ? t : 8 - t);
            }
            if (state[ns] == 0 || ng < g[ns] - 1e-6f) {
                g[ns] = ng;
                prev[ns] = s;
                dir[ns] = nd;
                state[ns] = 1;
                push(ng + H(cc), ns);
            }
        }
        if (openV[c] && openT[(1 - L) * N + c]) {
            int ns = (1 - L) * N + c;
            float ng = gs + vcost[c];
            if (state[ns] != 2 && (state[ns] == 0 || ng < g[ns] - 1e-6f)) {
                g[ns] = ng;
                prev[ns] = s;
                dir[ns] = -1;
                state[ns] = 1;
                push(ng + H(c), ns);
            }
        }
    }
    free(g);
    free(prev);
    free(dir);
    free(state);
    return result;
}
