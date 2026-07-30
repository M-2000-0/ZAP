import math

def _get_zpx_types():
    from .values import ZpxObject, ZpxBuiltin
    return ZpxObject, ZpxBuiltin

def _make_vec3(x=0.0, y=0.0, z=0.0):
    ZpxObject, _ = _get_zpx_types()
    v = ZpxObject()
    v.fields['__kind__'] = 'vec3'
    v.fields['x'] = float(x)
    v.fields['y'] = float(y)
    v.fields['z'] = float(z)
    return v

def _vec3_add(a, b):
    return _make_vec3(a.fields['x'] + b.fields['x'], a.fields['y'] + b.fields['y'], a.fields['z'] + b.fields['z'])

def _vec3_sub(a, b):
    return _make_vec3(a.fields['x'] - b.fields['x'], a.fields['y'] - b.fields['y'], a.fields['z'] - b.fields['z'])

def _vec3_scale(a, s):
    return _make_vec3(a.fields['x'] * s, a.fields['y'] * s, a.fields['z'] * s)

def _vec3_dot(a, b):
    return a.fields['x'] * b.fields['x'] + a.fields['y'] * b.fields['y'] + a.fields['z'] * b.fields['z']

def _vec3_cross(a, b):
    ax, ay, az = a.fields['x'], a.fields['y'], a.fields['z']
    bx, by, bz = b.fields['x'], b.fields['y'], b.fields['z']
    return _make_vec3(ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)

def _vec3_length(a):
    x, y, z = a.fields['x'], a.fields['y'], a.fields['z']
    return math.sqrt(x * x + y * y + z * z)

def _vec3_normalize(a):
    L = _vec3_length(a)
    if L == 0:
        return _make_vec3(0, 0, 0)
    return _make_vec3(a.fields['x'] / L, a.fields['y'] / L, a.fields['z'] / L)

def _vec3_distance(a, b):
    return _vec3_length(_vec3_sub(a, b))

def _vec3_lerp(a, b, t):
    return _make_vec3(
        a.fields['x'] + (b.fields['x'] - a.fields['x']) * t,
        a.fields['y'] + (b.fields['y'] - a.fields['y']) * t,
        a.fields['z'] + (b.fields['z'] - a.fields['z']) * t,
    )

def _vec3_neg(a):
    return _make_vec3(-a.fields['x'], -a.fields['y'], -a.fields['z'])

def _vec3_eq(a, b):
    return (a.fields['x'] == b.fields['x'] and
            a.fields['y'] == b.fields['y'] and
            a.fields['z'] == b.fields['z'])

def _vec3_str(a):
    return f"vec3({a.fields['x']}, {a.fields['y']}, {a.fields['z']})"

def _make_quat(x=0.0, y=0.0, z=0.0, w=1.0):
    ZpxObject, _ = _get_zpx_types()
    q = ZpxObject()
    q.fields['__kind__'] = 'quat'
    q.fields['x'] = float(x)
    q.fields['y'] = float(y)
    q.fields['z'] = float(z)
    q.fields['w'] = float(w)
    return q

def _quat_identity():
    return _make_quat(0, 0, 0, 1)

def _quat_from_axis_angle(ax, ay, az, angle):
    half = angle * 0.5
    s = math.sin(half)
    L = math.sqrt(ax * ax + ay * ay + az * az)
    if L == 0:
        return _quat_identity()
    return _make_quat(ax / L * s, ay / L * s, az / L * s, math.cos(half))

def _quat_from_euler(x, y, z):
    cx, cy, cz = math.cos(x * 0.5), math.cos(y * 0.5), math.cos(z * 0.5)
    sx, sy, sz = math.sin(x * 0.5), math.sin(y * 0.5), math.sin(z * 0.5)
    return _make_quat(
        sx * cy * cz - cx * sy * sz,
        cx * sy * cz + sx * cy * sz,
        cx * cy * sz - sx * sy * cz,
        cx * cy * cz + sx * sy * sz,
    )

def _quat_to_euler(q):
    x, y, z, w = q.fields['x'], q.fields['y'], q.fields['z'], q.fields['w']
    t0 = 2.0 * (w * x + y * z)
    t1 = 1.0 - 2.0 * (x * x + y * y)
    rx = math.atan2(t0, t1)
    t2 = 2.0 * (w * y - z * x)
    t2 = max(-1.0, min(1.0, t2))
    ry = math.asin(t2)
    t3 = 2.0 * (w * z + x * y)
    t4 = 1.0 - 2.0 * (y * y + z * z)
    rz = math.atan2(t3, t4)
    return _make_vec3(rx, ry, rz)

def _quat_mul(a, b):
    ax, ay, az, aw = a.fields['x'], a.fields['y'], a.fields['z'], a.fields['w']
    bx, by, bz, bw = b.fields['x'], b.fields['y'], b.fields['z'], b.fields['w']
    return _make_quat(
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )

def _quat_conjugate(q):
    return _make_quat(-q.fields['x'], -q.fields['y'], -q.fields['z'], q.fields['w'])

def _quat_length(q):
    x, y, z, w = q.fields['x'], q.fields['y'], q.fields['z'], q.fields['w']
    return math.sqrt(x * x + y * y + z * z + w * w)

def _quat_normalize(q):
    L = _quat_length(q)
    if L == 0:
        return _quat_identity()
    return _make_quat(q.fields['x'] / L, q.fields['y'] / L, q.fields['z'] / L, q.fields['w'] / L)

def _quat_rotate_vec3(q, v):
    p = _make_quat(v.fields['x'], v.fields['y'], v.fields['z'], 0)
    qc = _quat_conjugate(q)
    r = _quat_mul(_quat_mul(q, p), qc)
    return _make_vec3(r.fields['x'], r.fields['y'], r.fields['z'])

def _quat_slerp(a, b, t):
    ax, ay, az, aw = a.fields['x'], a.fields['y'], a.fields['z'], a.fields['w']
    bx, by, bz, bw = b.fields['x'], b.fields['y'], b.fields['z'], b.fields['w']
    cos_half = ax * bx + ay * by + az * bz + aw * bw
    if abs(cos_half) >= 1.0:
        return a
    sign = -1.0 if cos_half < 0 else 1.0
    cos_half = abs(cos_half)
    half_angle = math.acos(cos_half)
    sin_half = math.sqrt(1.0 - cos_half * cos_half)
    if abs(sin_half) < 0.001:
        return _make_quat(
            ax * 0.5 + bx * 0.5,
            ay * 0.5 + by * 0.5,
            az * 0.5 + bz * 0.5,
            aw * 0.5 + bw * 0.5,
        )
    a_ratio = math.sin((1 - t) * half_angle) / sin_half
    b_ratio = math.sin(t * half_angle) / sin_half
    return _make_quat(
        ax * a_ratio + bx * b_ratio * sign,
        ay * a_ratio + by * b_ratio * sign,
        az * a_ratio + bz * b_ratio * sign,
        aw * a_ratio + bw * b_ratio * sign,
    )

def _quat_str(q):
    return f"quat({q.fields['x']}, {q.fields['y']}, {q.fields['z']}, {q.fields['w']})"

def _make_mat4():
    ZpxObject, _ = _get_zpx_types()
    m = ZpxObject()
    m.fields['__kind__'] = 'mat4'
    m.fields['data'] = [1.0, 0.0, 0.0, 0.0,
                        0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 1.0, 0.0,
                        0.0, 0.0, 0.0, 1.0]
    return m

def _mat4_mul(a, b):
    ad = a.fields['data']
    bd = b.fields['data']
    result = [0.0] * 16
    for i in range(4):
        for j in range(4):
            for k in range(4):
                result[i * 4 + j] += ad[i * 4 + k] * bd[k * 4 + j]
    m = _make_mat4()
    m.fields['data'] = result
    return m

def _mat4_identity():
    return _make_mat4()

def _mat4_translate(x, y, z):
    m = _make_mat4()
    m.fields['data'][12] = float(x)
    m.fields['data'][13] = float(y)
    m.fields['data'][14] = float(z)
    return m

def _mat4_scale(x, y, z):
    m = _make_mat4()
    m.fields['data'][0] = float(x)
    m.fields['data'][5] = float(y)
    m.fields['data'][10] = float(z)
    return m

def _mat4_rotate_x(angle):
    m = _make_mat4()
    c, s = math.cos(angle), math.sin(angle)
    m.fields['data'][5] = c
    m.fields['data'][6] = -s
    m.fields['data'][9] = s
    m.fields['data'][10] = c
    return m

def _mat4_rotate_y(angle):
    m = _make_mat4()
    c, s = math.cos(angle), math.sin(angle)
    m.fields['data'][0] = c
    m.fields['data'][2] = s
    m.fields['data'][8] = -s
    m.fields['data'][10] = c
    return m

def _mat4_rotate_z(angle):
    m = _make_mat4()
    c, s = math.cos(angle), math.sin(angle)
    m.fields['data'][0] = c
    m.fields['data'][1] = -s
    m.fields['data'][4] = s
    m.fields['data'][5] = c
    return m

def _mat4_perspective(fov_y, aspect, near, far):
    m = _make_mat4()
    f = 1.0 / math.tan(fov_y * 0.5)
    m.fields['data'][0] = f / aspect
    m.fields['data'][5] = f
    m.fields['data'][10] = (far + near) / (near - far)
    m.fields['data'][11] = -1.0
    m.fields['data'][14] = (2.0 * far * near) / (near - far)
    m.fields['data'][15] = 0.0
    return m

def _mat4_look_at(eye, center, up):
    ZpxObject, _ = _get_zpx_types()
    f = _vec3_normalize(_vec3_sub(center, eye))
    s = _vec3_normalize(_vec3_cross(f, up))
    u = _vec3_cross(s, f)
    m = _make_mat4()
    m.fields['data'][0] = s.fields['x']
    m.fields['data'][1] = u.fields['x']
    m.fields['data'][2] = -f.fields['x']
    m.fields['data'][4] = s.fields['y']
    m.fields['data'][5] = u.fields['y']
    m.fields['data'][6] = -f.fields['y']
    m.fields['data'][8] = s.fields['z']
    m.fields['data'][9] = u.fields['z']
    m.fields['data'][10] = -f.fields['z']
    m.fields['data'][12] = -_vec3_dot(s, eye)
    m.fields['data'][13] = -_vec3_dot(u, eye)
    m.fields['data'][14] = _vec3_dot(f, eye)
    return m

def _mat4_transpose(m):
    d = m.fields['data']
    t = _make_mat4()
    t.fields['data'] = [
        d[0], d[4], d[8], d[12],
        d[1], d[5], d[9], d[13],
        d[2], d[6], d[10], d[14],
        d[3], d[7], d[11], d[15],
    ]
    return t

def _mat4_inverse(m):
    d = m.fields['data']
    a00, a01, a02, a03 = d[0], d[1], d[2], d[3]
    a10, a11, a12, a13 = d[4], d[5], d[6], d[7]
    a20, a21, a22, a23 = d[8], d[9], d[10], d[11]
    a30, a31, a32, a33 = d[12], d[13], d[14], d[15]

    b00 = a00 * a11 - a01 * a10
    b01 = a00 * a12 - a02 * a10
    b02 = a00 * a13 - a03 * a10
    b03 = a01 * a12 - a02 * a11
    b04 = a01 * a13 - a03 * a11
    b05 = a02 * a13 - a03 * a12
    b06 = a20 * a31 - a21 * a30
    b07 = a20 * a32 - a22 * a30
    b08 = a20 * a33 - a23 * a30
    b09 = a21 * a32 - a22 * a31
    b10 = a21 * a33 - a23 * a31
    b11 = a22 * a33 - a23 * a32

    det = b00 * b11 - b01 * b10 + b02 * b09 + b03 * b08 - b04 * b07 + b05 * b06
    if det == 0:
        return _make_mat4()
    inv_det = 1.0 / det

    result = [0.0] * 16
    result[0] = (a11 * b11 - a12 * b10 + a13 * b09) * inv_det
    result[1] = (-a01 * b11 + a02 * b10 - a03 * b09) * inv_det
    result[2] = (a31 * b05 - a32 * b04 + a33 * b03) * inv_det
    result[3] = (-a21 * b05 + a22 * b04 - a23 * b03) * inv_det
    result[4] = (-a10 * b11 + a12 * b08 - a13 * b07) * inv_det
    result[5] = (a00 * b11 - a02 * b08 + a03 * b07) * inv_det
    result[6] = (-a30 * b05 + a32 * b02 - a33 * b01) * inv_det
    result[7] = (a20 * b05 - a22 * b02 + a23 * b01) * inv_det
    result[8] = (a10 * b10 - a11 * b08 + a13 * b06) * inv_det
    result[9] = (-a00 * b10 + a01 * b08 - a03 * b06) * inv_det
    result[10] = (a30 * b04 - a31 * b02 + a33 * b00) * inv_det
    result[11] = (-a20 * b04 + a21 * b02 - a23 * b00) * inv_det
    result[12] = (-a10 * b09 + a11 * b07 - a12 * b06) * inv_det
    result[13] = (a00 * b09 - a01 * b07 + a02 * b06) * inv_det
    result[14] = (-a30 * b03 + a31 * b01 - a32 * b00) * inv_det
    result[15] = (a20 * b03 - a21 * b01 + a22 * b00) * inv_det

    m2 = _make_mat4()
    m2.fields['data'] = result
    return m2

def _mat4_str(m):
    d = m.fields['data']
    rows = []
    for i in range(4):
        rows.append(f"  [{d[i*4]:.3f}, {d[i*4+1]:.3f}, {d[i*4+2]:.3f}, {d[i*4+3]:.3f}]")
    return "mat4(\n" + "\n".join(rows) + "\n)"

def register_math_builtins(env):
    _, ZpxBuiltin = _get_zpx_types()
    math_fns = {
        'vec3': ZpxBuiltin(lambda x=0, y=0, z=0: _make_vec3(x, y, z), 'vec3'),
        'vec3_add': ZpxBuiltin(_vec3_add, 'vec3_add'),
        'vec3_sub': ZpxBuiltin(_vec3_sub, 'vec3_sub'),
        'vec3_scale': ZpxBuiltin(_vec3_scale, 'vec3_scale'),
        'vec3_dot': ZpxBuiltin(_vec3_dot, 'vec3_dot'),
        'vec3_cross': ZpxBuiltin(_vec3_cross, 'vec3_cross'),
        'vec3_length': ZpxBuiltin(_vec3_length, 'vec3_length'),
        'vec3_normalize': ZpxBuiltin(_vec3_normalize, 'vec3_normalize'),
        'vec3_distance': ZpxBuiltin(_vec3_distance, 'vec3_distance'),
        'vec3_lerp': ZpxBuiltin(_vec3_lerp, 'vec3_lerp'),
        'vec3_neg': ZpxBuiltin(_vec3_neg, 'vec3_neg'),
        'vec3_eq': ZpxBuiltin(_vec3_eq, 'vec3_eq'),
        'quat': ZpxBuiltin(lambda x=0, y=0, z=0, w=1: _make_quat(x, y, z, w), 'quat'),
        'quat_identity': ZpxBuiltin(_quat_identity, 'quat_identity'),
        'quat_from_axis_angle': ZpxBuiltin(lambda ax, ay, az, angle: _quat_from_axis_angle(ax, ay, az, angle), 'quat_from_axis_angle'),
        'quat_from_euler': ZpxBuiltin(lambda x, y, z: _quat_from_euler(x, y, z), 'quat_from_euler'),
        'quat_to_euler': ZpxBuiltin(_quat_to_euler, 'quat_to_euler'),
        'quat_mul': ZpxBuiltin(_quat_mul, 'quat_mul'),
        'quat_conjugate': ZpxBuiltin(_quat_conjugate, 'quat_conjugate'),
        'quat_length': ZpxBuiltin(_quat_length, 'quat_length'),
        'quat_normalize': ZpxBuiltin(_quat_normalize, 'quat_normalize'),
        'quat_rotate_vec3': ZpxBuiltin(_quat_rotate_vec3, 'quat_rotate_vec3'),
        'quat_slerp': ZpxBuiltin(_quat_slerp, 'quat_slerp'),
        'mat4': ZpxBuiltin(lambda: _make_mat4(), 'mat4'),
        'mat4_mul': ZpxBuiltin(_mat4_mul, 'mat4_mul'),
        'mat4_identity': ZpxBuiltin(_mat4_identity, 'mat4_identity'),
        'mat4_translate': ZpxBuiltin(lambda x, y, z: _mat4_translate(x, y, z), 'mat4_translate'),
        'mat4_scale': ZpxBuiltin(lambda x, y, z: _mat4_scale(x, y, z), 'mat4_scale'),
        'mat4_rotate_x': ZpxBuiltin(_mat4_rotate_x, 'mat4_rotate_x'),
        'mat4_rotate_y': ZpxBuiltin(_mat4_rotate_y, 'mat4_rotate_y'),
        'mat4_rotate_z': ZpxBuiltin(_mat4_rotate_z, 'mat4_rotate_z'),
        'mat4_perspective': ZpxBuiltin(_mat4_perspective, 'mat4_perspective'),
        'mat4_look_at': ZpxBuiltin(_mat4_look_at, 'mat4_look_at'),
        'mat4_transpose': ZpxBuiltin(_mat4_transpose, 'mat4_transpose'),
        'mat4_inverse': ZpxBuiltin(_mat4_inverse, 'mat4_inverse'),
    }
    for name, val in math_fns.items():
        env.define(name, val)
