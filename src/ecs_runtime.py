import threading

def _get_zpx_types():
    from .values import ZpxObject, ZpxList, ZpxBuiltin
    return ZpxObject, ZpxList, ZpxBuiltin

_worlds_lock = threading.Lock()

def _ecs_new_world():
    ZpxObject, ZpxList, _ = _get_zpx_types()
    obj = ZpxObject()
    obj.fields['__kind__'] = 'ecs_world'
    obj.fields['__entities__'] = {}
    obj.fields['__next_id__'] = 1
    obj.fields['__systems__'] = ZpxList([])
    return obj

def _ecs_world_create_entity(world, name=None):
    ZpxObject, _, _ = _get_zpx_types()
    eid = str(world.fields['__next_id__'])
    world.fields['__next_id__'] += 1
    entity = ZpxObject()
    entity.fields['__eid__'] = eid
    entity.fields['__name__'] = name or eid
    entity.fields['__components__'] = {}
    world.fields['__entities__'][eid] = entity
    return entity

def _ecs_world_add_component(world, entity, comp_type, comp_data):
    entities = world.fields['__entities__']
    eid = entity.fields['__eid__']
    if eid not in entities:
        raise Exception(f"Entity {eid} not found in world")
    comps = entities[eid].fields['__components__']
    type_name = comp_type if isinstance(comp_type, str) else comp_type.fields.get('__name__', str(comp_type))
    comps[type_name] = comp_data

def _ecs_world_get_component(world, entity, comp_type):
    entities = world.fields['__entities__']
    eid = entity.fields['__eid__']
    if eid not in entities:
        return None
    comps = entities[eid].fields['__components__']
    type_name = comp_type if isinstance(comp_type, str) else comp_type.fields.get('__name__', str(comp_type))
    return comps.get(type_name)

def _ecs_world_has_component(world, entity, comp_type):
    entities = world.fields['__entities__']
    eid = entity.fields['__eid__']
    if eid not in entities:
        return False
    comps = entities[eid].fields['__components__']
    type_name = comp_type if isinstance(comp_type, str) else comp_type.fields.get('__name__', str(comp_type))
    return type_name in comps

def _ecs_world_remove_component(world, entity, comp_type):
    entities = world.fields['__entities__']
    eid = entity.fields['__eid__']
    if eid not in entities:
        return
    comps = entities[eid].fields['__components__']
    type_name = comp_type if isinstance(comp_type, str) else comp_type.fields.get('__name__', str(comp_type))
    if type_name in comps:
        del comps[type_name]

def _ecs_world_query(world, comp_types):
    ZpxObject, ZpxList, _ = _get_zpx_types()
    entities = world.fields['__entities__']
    result = ZpxList([])
    for eid, entity in entities.items():
        comps = entity.fields['__components__']
        has_all = True
        for ct in comp_types:
            type_name = ct if isinstance(ct, str) else ct.fields.get('__name__', str(ct))
            if type_name not in comps:
                has_all = False
                break
        if has_all:
            result.append(entity)
    return result

def _ecs_world_register_system(world, system_name, requires, run_fn):
    ZpxObject, _, _ = _get_zpx_types()
    sys_obj = ZpxObject()
    sys_obj.fields['__name__'] = system_name
    sys_obj.fields['__requires__'] = requires
    sys_obj.fields['__run__'] = run_fn
    world.fields['__systems__'].append(sys_obj)

def _ecs_world_run_systems(world, dt):
    systems = world.fields['__systems__']
    for sys_obj in systems:
        run_fn = sys_obj.fields['__run__']
        if run_fn:
            run_fn(world, dt)

def _ecs_world_destroy_entity(world, entity):
    entities = world.fields['__entities__']
    eid = entity.fields['__eid__']
    if eid in entities:
        del entities[eid]

def register_ecs_builtins(env):
    _, _, ZpxBuiltin = _get_zpx_types()
    ecs_fns = {
        '_ecs_new_world': ZpxBuiltin(_ecs_new_world, '_ecs_new_world'),
        '_ecs_create_entity': ZpxBuiltin(_ecs_world_create_entity, '_ecs_create_entity'),
        '_ecs_add_component': ZpxBuiltin(_ecs_world_add_component, '_ecs_add_component'),
        '_ecs_get_component': ZpxBuiltin(_ecs_world_get_component, '_ecs_get_component'),
        '_ecs_has_component': ZpxBuiltin(_ecs_world_has_component, '_ecs_has_component'),
        '_ecs_remove_component': ZpxBuiltin(_ecs_world_remove_component, '_ecs_remove_component'),
        '_ecs_query': ZpxBuiltin(_ecs_world_query, '_ecs_query'),
        '_ecs_register_system': ZpxBuiltin(_ecs_world_register_system, '_ecs_register_system'),
        '_ecs_run_systems': ZpxBuiltin(_ecs_world_run_systems, '_ecs_run_systems'),
        '_ecs_destroy_entity': ZpxBuiltin(_ecs_world_destroy_entity, '_ecs_destroy_entity'),
    }
    for name, val in ecs_fns.items():
        env.define(name, val)
