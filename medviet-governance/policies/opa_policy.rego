package medviet.data_access

import future.keywords.if
import future.keywords.in

default allow := false

forbidden if {
	input.data_classification == "restricted"
	input.destination_country != "VN"
}

forbidden if {
	input.user.role == "ml_engineer"
	input.resource == "production_data"
	input.action == "delete"
}

allow if {
	not forbidden
	input.user.role == "admin"
}

allow if {
	not forbidden
	input.user.role == "ml_engineer"
	input.resource in {"training_data", "model_artifacts"}
	input.action in {"read", "write"}
}

allow if {
	not forbidden
	input.user.role == "data_analyst"
	input.resource in {"aggregated_metrics", "reports"}
	input.action in {"read", "write"}
}

allow if {
	not forbidden
	input.user.role == "intern"
	input.resource == "sandbox_data"
	input.action in {"read", "write"}
}
