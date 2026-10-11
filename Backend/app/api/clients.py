from flask import Blueprint, request, jsonify
from app import db
from app.models.client import Client

bp = Blueprint('clients', __name__, url_prefix='/clients')

@bp.route('', methods=['POST'])
def register_client():
    data = request.get_json()

    nombre_completo = data.get('nombre_completo') or data.get('name')
    rfc = (data.get('rfc') or data.get('tax_id', '')).strip().upper()
    
    tipo_persona_raw = data.get('tipo_persona') or data.get('person_type')
    tipo_persona = tipo_persona_raw.strip().upper() if tipo_persona_raw else None

    forma_pago_raw = data.get('forma_pago') or data.get('payment_method')
    forma_pago = forma_pago_raw.strip().upper() if forma_pago_raw else None

    contador_asignado_id = data.get('contador_asignado_id') or data.get('assigned_accountant_id')
    razon_social = data.get('razon_social') or data.get('business_name')
    giro = data.get('giro') or data.get('business_sector')
    telefono = data.get('telefono') or data.get('phone')
    correo = data.get('correo') or data.get('email')
    codigo_postal = data.get('codigo_postal')
    calle = data.get('calle')
    no_exterior = data.get('no_exterior') or data.get('ext_number')
    colonia = data.get('colonia')
    ciudad = data.get('ciudad')
    estado = data.get('estado')
    tiene_trabajadores = data.get('tiene_trabajadores', False)
    tipo_nomina = data.get('tipo_nomina')

    existing_client = Client.query.filter_by(rfc=rfc).first()
    if existing_client:
        return jsonify({
            "error": {
                "code": "DUPLICATE_RFC",
                "message": f"El RFC ya está registrado y pertenece al cliente: {existing_client.nombre_completo}"
            }
        }), 400

    try:
        new_client = Client(
            nombre_completo=nombre_completo,
            rfc=rfc,
            tipo_persona=tipo_persona,
            razon_social=razon_social,
            forma_pago=forma_pago,
            giro=giro,
            telefono=telefono,
            correo=correo,
            codigo_postal=codigo_postal,
            calle=calle,
            no_exterior=no_exterior,
            no_interior=data.get('no_interior'),
            colonia=colonia,
            ciudad=ciudad,
            estado=estado,
            tiene_trabajadores=tiene_trabajadores,
            tipo_nomina=data.get('tipo_nomina'),
            contador_asignado_id=contador_asignado_id,
            estatus='ACTIVO' 
        )

        db.session.add(new_client)
        db.session.commit()

        return jsonify({
            "message": "Cliente registrado exitosamente",
            "client": new_client.to_dict() if hasattr(new_client, 'to_dict') else {"rfc": rfc}
        }), 201

    except Exception as e:
        db.session.rollback()
        print("ERROR REAL DE PYTHON:", repr(e))
        return jsonify({"error": {"message": str(e)}}), 500