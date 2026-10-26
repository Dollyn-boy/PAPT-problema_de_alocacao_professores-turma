maximize
obj: 2.4 x_Ana_L_cia,EXA806_T01_ + 3 x_Ana_L_cia,EXA806_T02_ + 2.4 x_Pamela,EXA806_T02_ + 1.7999999999999998 x_Pamela,TEC217_TP02_ + 3 x_Elinaldo,TEC217_TP01_ + 0.6 x_Elinaldo,TEC217_TP02_ + 0.2 s_min - 0.1 z_Ana_L_cia,Seg_mat_ - 0.1 z_Ana_L_cia,Seg_vesp_ - 0.1 z_Ana_L_cia,Ter_mat_ - 0.1 z_Ana_L_cia,Ter_vesp_ - 0.1 z_Ana_L_cia,Qua_mat_ - 0.1 z_Ana_L_cia,Qua_vesp_ - 0.1 z_Ana_L_cia,Qui_mat_ - 0.1 z_Ana_L_cia,Qui_vesp_ - 0.1 z_Ana_L_cia,Sex_mat_ - 0.1 z_Ana_L_cia,Sex_vesp_ - 0.1 z_Pamela,Seg_mat_ - 0.1 z_Pamela,Seg_vesp_ - 0.1 z_Pamela,Ter_mat_ - 0.1 z_Pamela,Ter_vesp_ - 0.1 z_Pamela,Qua_mat_ - 0.1 z_Pamela,Qua_vesp_ - 0.1 z_Pamela,Qui_mat_ - 0.1 z_Pamela,Qui_vesp_ - 0.1 z_Pamela,Sex_mat_ - 0.1 z_Pamela,Sex_vesp_ - 0.1 z_Elinaldo,Seg_mat_ - 0.1 z_Elinaldo,Seg_vesp_ - 0.1 z_Elinaldo,Ter_mat_ - 0.1 z_Elinaldo,Ter_vesp_ - 0.1 z_Elinaldo,Qua_mat_ - 0.1 z_Elinaldo,Qua_vesp_ - 0.1 z_Elinaldo,Qui_mat_ - 0.1 z_Elinaldo,Qui_vesp_ - 0.1 z_Elinaldo,Sex_mat_ - 0.1 z_Elinaldo,Sex_vesp_ - 0.1 g_max
subject to
_elegibilidade_Ana_L_cia,EXA806_T01_: 1 x_Ana_L_cia,EXA806_T01_ <= 1
_elegibilidade_Pamela,EXA806_T01_: 1 x_Pamela,EXA806_T01_ <= 0
_elegibilidade_Elinaldo,EXA806_T01_: 1 x_Elinaldo,EXA806_T01_ <= 0
_elegibilidade_Ana_L_cia,EXA806_T02_: 1 x_Ana_L_cia,EXA806_T02_ <= 1
_elegibilidade_Pamela,EXA806_T02_: 1 x_Pamela,EXA806_T02_ <= 1
_elegibilidade_Elinaldo,EXA806_T02_: 1 x_Elinaldo,EXA806_T02_ <= 0
_elegibilidade_Ana_L_cia,TEC217_TP01_: 1 x_Ana_L_cia,TEC217_TP01_ <= 0
_elegibilidade_Pamela,TEC217_TP01_: 1 x_Pamela,TEC217_TP01_ <= 0
_elegibilidade_Elinaldo,TEC217_TP01_: 1 x_Elinaldo,TEC217_TP01_ <= 1
_elegibilidade_Ana_L_cia,TEC217_TP02_: 1 x_Ana_L_cia,TEC217_TP02_ <= 0
_elegibilidade_Pamela,TEC217_TP02_: 1 x_Pamela,TEC217_TP02_ <= 1
_elegibilidade_Elinaldo,TEC217_TP02_: 1 x_Elinaldo,TEC217_TP02_ <= 1
carga_max_Ana_L_cia_: 4 x_Ana_L_cia,EXA806_T01_ + 4 x_Ana_L_cia,EXA806_T02_ + 4 x_Ana_L_cia,TEC217_TP01_ + 4 x_Ana_L_cia,TEC217_TP02_ <= 8
carga_max_Pamela_: 4 x_Pamela,EXA806_T01_ + 4 x_Pamela,EXA806_T02_ + 4 x_Pamela,TEC217_TP01_ + 4 x_Pamela,TEC217_TP02_ <= 8
carga_max_Elinaldo_: 4 x_Elinaldo,EXA806_T01_ + 4 x_Elinaldo,EXA806_T02_ + 4 x_Elinaldo,TEC217_TP01_ + 4 x_Elinaldo,TEC217_TP02_ <= 8
piso_satisfacao_Ana_L_cia_: -4 x_Ana_L_cia,EXA806_T01_ - 5 x_Ana_L_cia,EXA806_T02_ + 1 s_min <= 0
piso_satisfacao_Pamela_: -4 x_Pamela,EXA806_T02_ - 3 x_Pamela,TEC217_TP02_ + 1 s_min <= 0
piso_satisfacao_Elinaldo_: -5 x_Elinaldo,TEC217_TP01_ - 1 x_Elinaldo,TEC217_TP02_ + 1 s_min <= 0
liga_disciplina_Ana_L_cia,EXA806_T01_: 1 x_Ana_L_cia,EXA806_T01_ - 1 g_Ana_L_cia,EXA806_ <= 0
liga_disciplina_Pamela,EXA806_T01_: 1 x_Pamela,EXA806_T01_ - 1 g_Pamela,EXA806_ <= 0
liga_disciplina_Elinaldo,EXA806_T01_: 1 x_Elinaldo,EXA806_T01_ - 1 g_Elinaldo,EXA806_ <= 0
liga_disciplina_Ana_L_cia,EXA806_T02_: 1 x_Ana_L_cia,EXA806_T02_ - 1 g_Ana_L_cia,EXA806_ <= 0
liga_disciplina_Pamela,EXA806_T02_: 1 x_Pamela,EXA806_T02_ - 1 g_Pamela,EXA806_ <= 0
liga_disciplina_Elinaldo,EXA806_T02_: 1 x_Elinaldo,EXA806_T02_ - 1 g_Elinaldo,EXA806_ <= 0
liga_disciplina_Ana_L_cia,TEC217_TP01_: 1 x_Ana_L_cia,TEC217_TP01_ - 1 g_Ana_L_cia,TEC217_ <= 0
liga_disciplina_Pamela,TEC217_TP01_: 1 x_Pamela,TEC217_TP01_ - 1 g_Pamela,TEC217_ <= 0
liga_disciplina_Elinaldo,TEC217_TP01_: 1 x_Elinaldo,TEC217_TP01_ - 1 g_Elinaldo,TEC217_ <= 0
liga_disciplina_Ana_L_cia,TEC217_TP02_: 1 x_Ana_L_cia,TEC217_TP02_ - 1 g_Ana_L_cia,TEC217_ <= 0
liga_disciplina_Pamela,TEC217_TP02_: 1 x_Pamela,TEC217_TP02_ - 1 g_Pamela,TEC217_ <= 0
liga_disciplina_Elinaldo,TEC217_TP02_: 1 x_Elinaldo,TEC217_TP02_ - 1 g_Elinaldo,TEC217_ <= 0
liga_disciplina_reversa_Ana_L_cia,EXA806_: -1 x_Ana_L_cia,EXA806_T01_ - 1 x_Ana_L_cia,EXA806_T02_ + 1 g_Ana_L_cia,EXA806_ <= 0
liga_disciplina_reversa_Pamela,EXA806_: -1 x_Pamela,EXA806_T01_ - 1 x_Pamela,EXA806_T02_ + 1 g_Pamela,EXA806_ <= 0
liga_disciplina_reversa_Elinaldo,EXA806_: -1 x_Elinaldo,EXA806_T01_ - 1 x_Elinaldo,EXA806_T02_ + 1 g_Elinaldo,EXA806_ <= 0
liga_disciplina_reversa_Ana_L_cia,TEC217_: -1 x_Ana_L_cia,TEC217_TP01_ - 1 x_Ana_L_cia,TEC217_TP02_ + 1 g_Ana_L_cia,TEC217_ <= 0
liga_disciplina_reversa_Pamela,TEC217_: -1 x_Pamela,TEC217_TP01_ - 1 x_Pamela,TEC217_TP02_ + 1 g_Pamela,TEC217_ <= 0
liga_disciplina_reversa_Elinaldo,TEC217_: -1 x_Elinaldo,TEC217_TP01_ - 1 x_Elinaldo,TEC217_TP02_ + 1 g_Elinaldo,TEC217_ <= 0
conflito_slot_Ana_L_cia,("Seg",_"17_30")_: 1 x_Ana_L_cia,EXA806_T01_ <= 1
conflito_slot_Pamela,("Seg",_"17_30")_: 1 x_Pamela,EXA806_T01_ <= 1
conflito_slot_Elinaldo,("Seg",_"17_30")_: 1 x_Elinaldo,EXA806_T01_ <= 1
conflito_slot_Ana_L_cia,("Qua",_"17_30")_: 1 x_Ana_L_cia,EXA806_T01_ <= 1
conflito_slot_Pamela,("Qua",_"17_30")_: 1 x_Pamela,EXA806_T01_ <= 1
conflito_slot_Elinaldo,("Qua",_"17_30")_: 1 x_Elinaldo,EXA806_T01_ <= 1
conflito_slot_Ana_L_cia,("Ter",_"9_30")_: 1 x_Ana_L_cia,EXA806_T02_ <= 1
conflito_slot_Pamela,("Ter",_"9_30")_: 1 x_Pamela,EXA806_T02_ <= 1
conflito_slot_Elinaldo,("Ter",_"9_30")_: 1 x_Elinaldo,EXA806_T02_ <= 1
conflito_slot_Ana_L_cia,("Qui",_"9_30")_: 1 x_Ana_L_cia,EXA806_T02_ <= 1
conflito_slot_Pamela,("Qui",_"9_30")_: 1 x_Pamela,EXA806_T02_ <= 1
conflito_slot_Elinaldo,("Qui",_"9_30")_: 1 x_Elinaldo,EXA806_T02_ <= 1
conflito_slot_Ana_L_cia,("Seg",_"13_30")_: 1 x_Ana_L_cia,TEC217_TP01_ <= 1
conflito_slot_Pamela,("Seg",_"13_30")_: 1 x_Pamela,TEC217_TP01_ <= 1
conflito_slot_Elinaldo,("Seg",_"13_30")_: 1 x_Elinaldo,TEC217_TP01_ <= 1
conflito_slot_Ana_L_cia,("Qua",_"13_30")_: 1 x_Ana_L_cia,TEC217_TP01_ <= 1
conflito_slot_Pamela,("Qua",_"13_30")_: 1 x_Pamela,TEC217_TP01_ <= 1
conflito_slot_Elinaldo,("Qua",_"13_30")_: 1 x_Elinaldo,TEC217_TP01_ <= 1
conflito_slot_Ana_L_cia,("Ter",_"15_30")_: 1 x_Ana_L_cia,TEC217_TP02_ <= 1
conflito_slot_Pamela,("Ter",_"15_30")_: 1 x_Pamela,TEC217_TP02_ <= 1
conflito_slot_Elinaldo,("Ter",_"15_30")_: 1 x_Elinaldo,TEC217_TP02_ <= 1
conflito_slot_Ana_L_cia,("Qui",_"15_30")_: 1 x_Ana_L_cia,TEC217_TP02_ <= 1
conflito_slot_Pamela,("Qui",_"15_30")_: 1 x_Pamela,TEC217_TP02_ <= 1
conflito_slot_Elinaldo,("Qui",_"15_30")_: 1 x_Elinaldo,TEC217_TP02_ <= 1
liga_turno_Ana_L_cia,EXA806_T01,Seg_vesp_: 1 x_Ana_L_cia,EXA806_T01_ - 1 z_Ana_L_cia,Seg_vesp_ <= 0
liga_turno_Ana_L_cia,EXA806_T01,Qua_vesp_: 1 x_Ana_L_cia,EXA806_T01_ - 1 z_Ana_L_cia,Qua_vesp_ <= 0
liga_turno_Ana_L_cia,EXA806_T02,Ter_mat_: 1 x_Ana_L_cia,EXA806_T02_ - 1 z_Ana_L_cia,Ter_mat_ <= 0
liga_turno_Ana_L_cia,EXA806_T02,Qui_mat_: 1 x_Ana_L_cia,EXA806_T02_ - 1 z_Ana_L_cia,Qui_mat_ <= 0
liga_turno_Ana_L_cia,TEC217_TP01,Seg_vesp_: 1 x_Ana_L_cia,TEC217_TP01_ - 1 z_Ana_L_cia,Seg_vesp_ <= 0
liga_turno_Ana_L_cia,TEC217_TP01,Qua_vesp_: 1 x_Ana_L_cia,TEC217_TP01_ - 1 z_Ana_L_cia,Qua_vesp_ <= 0
liga_turno_Ana_L_cia,TEC217_TP02,Ter_vesp_: 1 x_Ana_L_cia,TEC217_TP02_ - 1 z_Ana_L_cia,Ter_vesp_ <= 0
liga_turno_Ana_L_cia,TEC217_TP02,Qui_vesp_: 1 x_Ana_L_cia,TEC217_TP02_ - 1 z_Ana_L_cia,Qui_vesp_ <= 0
liga_turno_Pamela,EXA806_T01,Seg_vesp_: 1 x_Pamela,EXA806_T01_ - 1 z_Pamela,Seg_vesp_ <= 0
liga_turno_Pamela,EXA806_T01,Qua_vesp_: 1 x_Pamela,EXA806_T01_ - 1 z_Pamela,Qua_vesp_ <= 0
liga_turno_Pamela,EXA806_T02,Ter_mat_: 1 x_Pamela,EXA806_T02_ - 1 z_Pamela,Ter_mat_ <= 0
liga_turno_Pamela,EXA806_T02,Qui_mat_: 1 x_Pamela,EXA806_T02_ - 1 z_Pamela,Qui_mat_ <= 0
liga_turno_Pamela,TEC217_TP01,Seg_vesp_: 1 x_Pamela,TEC217_TP01_ - 1 z_Pamela,Seg_vesp_ <= 0
liga_turno_Pamela,TEC217_TP01,Qua_vesp_: 1 x_Pamela,TEC217_TP01_ - 1 z_Pamela,Qua_vesp_ <= 0
liga_turno_Pamela,TEC217_TP02,Ter_vesp_: 1 x_Pamela,TEC217_TP02_ - 1 z_Pamela,Ter_vesp_ <= 0
liga_turno_Pamela,TEC217_TP02,Qui_vesp_: 1 x_Pamela,TEC217_TP02_ - 1 z_Pamela,Qui_vesp_ <= 0
liga_turno_Elinaldo,EXA806_T01,Seg_vesp_: 1 x_Elinaldo,EXA806_T01_ - 1 z_Elinaldo,Seg_vesp_ <= 0
liga_turno_Elinaldo,EXA806_T01,Qua_vesp_: 1 x_Elinaldo,EXA806_T01_ - 1 z_Elinaldo,Qua_vesp_ <= 0
liga_turno_Elinaldo,EXA806_T02,Ter_mat_: 1 x_Elinaldo,EXA806_T02_ - 1 z_Elinaldo,Ter_mat_ <= 0
liga_turno_Elinaldo,EXA806_T02,Qui_mat_: 1 x_Elinaldo,EXA806_T02_ - 1 z_Elinaldo,Qui_mat_ <= 0
liga_turno_Elinaldo,TEC217_TP01,Seg_vesp_: 1 x_Elinaldo,TEC217_TP01_ - 1 z_Elinaldo,Seg_vesp_ <= 0
liga_turno_Elinaldo,TEC217_TP01,Qua_vesp_: 1 x_Elinaldo,TEC217_TP01_ - 1 z_Elinaldo,Qua_vesp_ <= 0
liga_turno_Elinaldo,TEC217_TP02,Ter_vesp_: 1 x_Elinaldo,TEC217_TP02_ - 1 z_Elinaldo,Ter_vesp_ <= 0
liga_turno_Elinaldo,TEC217_TP02,Qui_vesp_: 1 x_Elinaldo,TEC217_TP02_ - 1 z_Elinaldo,Qui_vesp_ <= 0
liga_turno_reversa_Ana_L_cia,Seg_mat_: 1 z_Ana_L_cia,Seg_mat_ <= 0
liga_turno_reversa_Pamela,Seg_mat_: 1 z_Pamela,Seg_mat_ <= 0
liga_turno_reversa_Elinaldo,Seg_mat_: 1 z_Elinaldo,Seg_mat_ <= 0
liga_turno_reversa_Ana_L_cia,Seg_vesp_: -1 x_Ana_L_cia,EXA806_T01_ - 1 x_Ana_L_cia,TEC217_TP01_ + 1 z_Ana_L_cia,Seg_vesp_ <= 0
liga_turno_reversa_Pamela,Seg_vesp_: -1 x_Pamela,EXA806_T01_ - 1 x_Pamela,TEC217_TP01_ + 1 z_Pamela,Seg_vesp_ <= 0
liga_turno_reversa_Elinaldo,Seg_vesp_: -1 x_Elinaldo,EXA806_T01_ - 1 x_Elinaldo,TEC217_TP01_ + 1 z_Elinaldo,Seg_vesp_ <= 0
liga_turno_reversa_Ana_L_cia,Ter_mat_: -1 x_Ana_L_cia,EXA806_T02_ + 1 z_Ana_L_cia,Ter_mat_ <= 0
liga_turno_reversa_Pamela,Ter_mat_: -1 x_Pamela,EXA806_T02_ + 1 z_Pamela,Ter_mat_ <= 0
liga_turno_reversa_Elinaldo,Ter_mat_: -1 x_Elinaldo,EXA806_T02_ + 1 z_Elinaldo,Ter_mat_ <= 0
liga_turno_reversa_Ana_L_cia,Ter_vesp_: -1 x_Ana_L_cia,TEC217_TP02_ + 1 z_Ana_L_cia,Ter_vesp_ <= 0
liga_turno_reversa_Pamela,Ter_vesp_: -1 x_Pamela,TEC217_TP02_ + 1 z_Pamela,Ter_vesp_ <= 0
liga_turno_reversa_Elinaldo,Ter_vesp_: -1 x_Elinaldo,TEC217_TP02_ + 1 z_Elinaldo,Ter_vesp_ <= 0
liga_turno_reversa_Ana_L_cia,Qua_mat_: 1 z_Ana_L_cia,Qua_mat_ <= 0
liga_turno_reversa_Pamela,Qua_mat_: 1 z_Pamela,Qua_mat_ <= 0
liga_turno_reversa_Elinaldo,Qua_mat_: 1 z_Elinaldo,Qua_mat_ <= 0
liga_turno_reversa_Ana_L_cia,Qua_vesp_: -1 x_Ana_L_cia,EXA806_T01_ - 1 x_Ana_L_cia,TEC217_TP01_ + 1 z_Ana_L_cia,Qua_vesp_ <= 0
liga_turno_reversa_Pamela,Qua_vesp_: -1 x_Pamela,EXA806_T01_ - 1 x_Pamela,TEC217_TP01_ + 1 z_Pamela,Qua_vesp_ <= 0
liga_turno_reversa_Elinaldo,Qua_vesp_: -1 x_Elinaldo,EXA806_T01_ - 1 x_Elinaldo,TEC217_TP01_ + 1 z_Elinaldo,Qua_vesp_ <= 0
liga_turno_reversa_Ana_L_cia,Qui_mat_: -1 x_Ana_L_cia,EXA806_T02_ + 1 z_Ana_L_cia,Qui_mat_ <= 0
liga_turno_reversa_Pamela,Qui_mat_: -1 x_Pamela,EXA806_T02_ + 1 z_Pamela,Qui_mat_ <= 0
liga_turno_reversa_Elinaldo,Qui_mat_: -1 x_Elinaldo,EXA806_T02_ + 1 z_Elinaldo,Qui_mat_ <= 0
liga_turno_reversa_Ana_L_cia,Qui_vesp_: -1 x_Ana_L_cia,TEC217_TP02_ + 1 z_Ana_L_cia,Qui_vesp_ <= 0
liga_turno_reversa_Pamela,Qui_vesp_: -1 x_Pamela,TEC217_TP02_ + 1 z_Pamela,Qui_vesp_ <= 0
liga_turno_reversa_Elinaldo,Qui_vesp_: -1 x_Elinaldo,TEC217_TP02_ + 1 z_Elinaldo,Qui_vesp_ <= 0
liga_turno_reversa_Ana_L_cia,Sex_mat_: 1 z_Ana_L_cia,Sex_mat_ <= 0
liga_turno_reversa_Pamela,Sex_mat_: 1 z_Pamela,Sex_mat_ <= 0
liga_turno_reversa_Elinaldo,Sex_mat_: 1 z_Elinaldo,Sex_mat_ <= 0
liga_turno_reversa_Ana_L_cia,Sex_vesp_: 1 z_Ana_L_cia,Sex_vesp_ <= 0
liga_turno_reversa_Pamela,Sex_vesp_: 1 z_Pamela,Sex_vesp_ <= 0
liga_turno_reversa_Elinaldo,Sex_vesp_: 1 z_Elinaldo,Sex_vesp_ <= 0
carga_min_Ana_L_cia_: 4 x_Ana_L_cia,EXA806_T01_ + 4 x_Ana_L_cia,EXA806_T02_ + 4 x_Ana_L_cia,TEC217_TP01_ + 4 x_Ana_L_cia,TEC217_TP02_ >= 4
carga_min_Pamela_: 4 x_Pamela,EXA806_T01_ + 4 x_Pamela,EXA806_T02_ + 4 x_Pamela,TEC217_TP01_ + 4 x_Pamela,TEC217_TP02_ >= 4
carga_min_Elinaldo_: 4 x_Elinaldo,EXA806_T01_ + 4 x_Elinaldo,EXA806_T02_ + 4 x_Elinaldo,TEC217_TP01_ + 4 x_Elinaldo,TEC217_TP02_ >= 4
teto_disciplinas_Ana_L_cia_: -1 g_Ana_L_cia,EXA806_ - 1 g_Ana_L_cia,TEC217_ + 1 g_max >= 0
teto_disciplinas_Pamela_: -1 g_Pamela,EXA806_ - 1 g_Pamela,TEC217_ + 1 g_max >= 0
teto_disciplinas_Elinaldo_: -1 g_Elinaldo,EXA806_ - 1 g_Elinaldo,TEC217_ + 1 g_max >= 0
cobertura_EXA806_T01_: 1 x_Ana_L_cia,EXA806_T01_ + 1 x_Pamela,EXA806_T01_ + 1 x_Elinaldo,EXA806_T01_ = 1
cobertura_EXA806_T02_: 1 x_Ana_L_cia,EXA806_T02_ + 1 x_Pamela,EXA806_T02_ + 1 x_Elinaldo,EXA806_T02_ = 1
cobertura_TEC217_TP01_: 1 x_Ana_L_cia,TEC217_TP01_ + 1 x_Pamela,TEC217_TP01_ + 1 x_Elinaldo,TEC217_TP01_ = 1
cobertura_TEC217_TP02_: 1 x_Ana_L_cia,TEC217_TP02_ + 1 x_Pamela,TEC217_TP02_ + 1 x_Elinaldo,TEC217_TP02_ = 1
Bounds
s_min >= 0
g_max >= 0
General
s_min
g_max
Binary
x_Ana_L_cia,EXA806_T01_
x_Pamela,EXA806_T01_
x_Elinaldo,EXA806_T01_
x_Ana_L_cia,EXA806_T02_
x_Pamela,EXA806_T02_
x_Elinaldo,EXA806_T02_
x_Ana_L_cia,TEC217_TP01_
x_Pamela,TEC217_TP01_
x_Elinaldo,TEC217_TP01_
x_Ana_L_cia,TEC217_TP02_
x_Pamela,TEC217_TP02_
x_Elinaldo,TEC217_TP02_
z_Ana_L_cia,Seg_mat_
z_Pamela,Seg_mat_
z_Elinaldo,Seg_mat_
z_Ana_L_cia,Seg_vesp_
z_Pamela,Seg_vesp_
z_Elinaldo,Seg_vesp_
z_Ana_L_cia,Ter_mat_
z_Pamela,Ter_mat_
z_Elinaldo,Ter_mat_
z_Ana_L_cia,Ter_vesp_
z_Pamela,Ter_vesp_
z_Elinaldo,Ter_vesp_
z_Ana_L_cia,Qua_mat_
z_Pamela,Qua_mat_
z_Elinaldo,Qua_mat_
z_Ana_L_cia,Qua_vesp_
z_Pamela,Qua_vesp_
z_Elinaldo,Qua_vesp_
z_Ana_L_cia,Qui_mat_
z_Pamela,Qui_mat_
z_Elinaldo,Qui_mat_
z_Ana_L_cia,Qui_vesp_
z_Pamela,Qui_vesp_
z_Elinaldo,Qui_vesp_
z_Ana_L_cia,Sex_mat_
z_Pamela,Sex_mat_
z_Elinaldo,Sex_mat_
z_Ana_L_cia,Sex_vesp_
z_Pamela,Sex_vesp_
z_Elinaldo,Sex_vesp_
g_Ana_L_cia,EXA806_
g_Pamela,EXA806_
g_Elinaldo,EXA806_
g_Ana_L_cia,TEC217_
g_Pamela,TEC217_
g_Elinaldo,TEC217_
End
